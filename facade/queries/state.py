from typing import Optional, List, Dict, Any
import datetime

import jsonpatch  # type: ignore[import-untyped]
import strawberry
from django.db.models import Min, Max, QuerySet
from django.core.exceptions import ObjectDoesNotExist

from facade import models, types, inputs, managers
from kante.types import Info
from facade.logic import get_latest_state


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def _get_boundary_aggregates(queryset: QuerySet) -> Optional[Dict[str, Any]]:
    """Helper to extract common start/end aggregations for boundary calculations."""
    agg = queryset.aggregate(
        start_global_revision=Min("global_current_revision"),
        end_global_revision=Max("global_future_revision"),
        start_time=Min("timestamp"),
        end_time=Max("timestamp"),
    )
    if agg["start_global_revision"] is None:
        return None
    return agg


def _get_state_ids(session_id: str | None) -> List[str]:
    """Get distinct state_ids from both Snapshots and Patches."""
    snapshot_qs = models.Snapshot.objects.all()
    patch_qs = models.Patch.objects.all()

    if session_id:
        snapshot_qs = snapshot_qs.filter(session_id=session_id)
        patch_qs = patch_qs.filter(session_id=session_id)

    snapshot_ids = set(snapshot_qs.values_list("state_id", flat=True))
    patch_ids = set(patch_qs.values_list("state_id", flat=True))
    return sorted(list(snapshot_ids.union(patch_ids)))


def _get_state_at_revision(
    target_revision: int,
    state_id: str,
    session_id: str | None,
    use_global_revision: bool,
) -> Optional[types.Snapshot]:
    """Calculates the state of a specific document at a given revision by applying JSON patches."""
    snapshot_rev_field = "global_revision" if use_global_revision else "revision"
    patch_current_field = "global_current_revision" if use_global_revision else "current_revision"
    patch_future_field = "global_future_revision" if use_global_revision else "future_revision"

    # 1. Fetch the closest anchor snapshot prior to or at the target revision
    snapshot_qs = models.Snapshot.objects.filter(state_id=state_id)
    if session_id:
        snapshot_qs = snapshot_qs.filter(session_id=session_id)

    anchor_snapshot = snapshot_qs.filter(**{f"{snapshot_rev_field}__lte": target_revision}).order_by(f"-{snapshot_rev_field}").first()

    if not anchor_snapshot:
        return None

    # 2. Fetch all patches between the anchor snapshot and the target revision
    patch_start_rev = getattr(anchor_snapshot, snapshot_rev_field) or 0
    patch_qs = models.Patch.objects.filter(state_id=state_id)
    if session_id:
        patch_qs = patch_qs.filter(session_id=session_id)

    patch_qs = patch_qs.filter(**{f"{patch_current_field}__gte": patch_start_rev, f"{patch_future_field}__lte": target_revision}).order_by(patch_current_field)

    # 3. Batch apply JSON patches
    state_data = anchor_snapshot.value
    last_snapshot = anchor_snapshot
    patch_docs = []
    last_patch = None

    for patch in patch_qs:
        patch_doc = {"op": patch.op, "path": patch.path}
        if patch.op != "remove":
            patch_doc["value"] = patch.value
        patch_docs.append(patch_doc)
        last_patch = patch

    if patch_docs:
        state_data = jsonpatch.apply_patch(state_data, patch_docs, in_place=False)
        last_snapshot = types.Snapshot(value=state_data, timestamp=last_patch.timestamp, revision=last_patch.future_revision, global_revision=last_patch.global_future_revision, session_id=last_patch.session_id, state=last_patch.state)

    return last_snapshot


# -----------------------------------------------------------------------------
# GraphQL Resolvers
# -----------------------------------------------------------------------------


def state_for(
    info: Info,
    agent: strawberry.ID,
    state_hash: str | None = None,
    demand: inputs.SchemaDemandInput | None = None,
) -> types.State:
    """Get a state for an agent."""
    agent_inst = models.Agent.objects.get(id=agent)

    if demand and demand.matches:
        state_ids = managers.get_state_ids_by_demands(demand.matches)
        return models.State.objects.get(agent=agent_inst, id__in=state_ids)

    if state_hash:
        return models.State.objects.get(agent=agent_inst, state_schema__hash=state_hash)

    raise ValueError("Either state_hash or a valid demand must be provided")


def task_boundaries(
    info: Info,
    correlation_id: str,
    state_id: strawberry.ID | None = None,
) -> Optional[types.TaskBoundary]:
    """Retrieve min/max revisions and times for a task correlation ID."""
    queryset = models.Patch.objects.filter(assignation__reference=correlation_id)
    if state_id:
        queryset = queryset.filter(state_id=state_id)

    agg = _get_boundary_aggregates(queryset)
    if not agg:
        return None

    return types.TaskBoundary(correlation_id=correlation_id, **agg)


def session_boundaries(
    info: Info,
    session_id: strawberry.ID,
    state_id: strawberry.ID | None = None,
) -> Optional[types.SessionBoundary]:
    """Retrieve min/max revisions and times for a specific session."""
    queryset = models.Patch.objects.filter(session_id=session_id)
    if state_id:
        queryset = queryset.filter(state_id=state_id)

    agg = _get_boundary_aggregates(queryset)
    if not agg:
        return None

    return types.SessionBoundary(session_id=session_id, **agg)


def state_at_global_rev(
    info: Info,
    global_revision: int,
    state_id: strawberry.ID | None = None,
    session_id: str | None = None,
) -> List[types.Snapshot]:
    state_ids = [str(state_id)] if state_id else _get_state_ids(session_id)

    results = []
    for sid in state_ids:
        res = _get_state_at_revision(global_revision, sid, session_id, use_global_revision=True)
        if res:
            results.append(res)

    return results


def state_at_local_rev(
    info: Info,
    revision: int,
    state_id: strawberry.ID | None = None,
    session_id: str | None = None,
) -> List[types.Snapshot]:
    state_ids = [str(state_id)] if state_id else _get_state_ids(session_id)

    results = []
    for sid in state_ids:
        res = _get_state_at_revision(revision, sid, session_id, use_global_revision=False)
        if res:
            results.append(res)

    return results


def forward_events_after_rev(
    info: Info,
    global_revision: int,
    state_id: strawberry.ID | None = None,
    session_id: str | None = None,
    count: int = 100,
) -> List[types.Patch]:
    queryset = models.Patch.objects.filter(global_current_revision__gte=global_revision)
    if state_id:
        queryset = queryset.filter(state_id=state_id)
    if session_id:
        queryset = queryset.filter(session_id=session_id)

    return list(queryset.order_by("global_current_revision", "state_id", "current_revision")[:count])


def patch_events_between_global_revs(
    info: Info,
    from_global_revision: int,
    to_global_revision: int,
    state_ids: List[strawberry.ID] | None = None,
    session_id: str | None = None,
) -> List[types.Patch]:
    if to_global_revision < from_global_revision:
        return []

    queryset = models.Patch.objects.filter(global_current_revision__gte=from_global_revision, global_future_revision__lte=to_global_revision)
    if state_ids:
        queryset = queryset.filter(state_id__in=state_ids)
    if session_id:
        queryset = queryset.filter(session_id=session_id)

    return list(queryset.order_by("global_current_revision", "state_id", "current_revision"))


def snapshots_around_rev(
    info: Info,
    revision: int,
    state_id: strawberry.ID | None = None,
    session_id: str | None = None,
    before: int = 1,
    after: int = 1,
) -> List[types.Snapshot]:
    target_state_ids = [str(state_id)] if state_id else _get_state_ids(session_id)
    collected: List[types.Snapshot] = []

    for sid in target_state_ids:
        qs_before = models.Snapshot.objects.filter(state_id=sid, revision__lte=revision)
        qs_after = models.Snapshot.objects.filter(state_id=sid, revision__gt=revision)

        if session_id:
            qs_before = qs_before.filter(session_id=session_id)
            qs_after = qs_after.filter(session_id=session_id)

        before_list = list(qs_before.order_by("-revision")[:before][::-1])  # Reverse to chronological
        after_list = list(qs_after.order_by("revision")[:after])

        collected.extend(before_list + after_list)

    return collected


# -----------------------------------------------------------------------------
# Checkouts & State Values
# -----------------------------------------------------------------------------


@strawberry.type
class StateValue:
    """A state value and its schema."""

    state_id: strawberry.ID = strawberry.field(description="The ID of the state")
    value: strawberry.scalars.JSON = strawberry.field(description="The state value")
    global_revision: int | None = strawberry.field(description="The global revision of this state")
    forward_patches: List[types.Patch] = strawberry.field(description="The patches that can be applied to move forward from this state")


def checkout(
    info: Info,
    state: strawberry.ID,
    session_id: strawberry.ID | None = None,
    global_revision: int | None = None,
    timestamp: datetime.datetime | None = None,
    forward_patch_count: int = 0,
) -> StateValue:
    """Checkout a state at a specific revision."""
    state_inst = models.State.objects.get(id=state)

    if timestamp:
        latest_patch = models.Patch.objects.filter(state_id=state, agent=state_inst.agent, timestamp__lte=timestamp).order_by("-timestamp").first()

        if not latest_patch:
            raise ObjectDoesNotExist(f"No patches found for state {state} before timestamp {timestamp}")

        target_global_rev = latest_patch.global_rev
        target_session = latest_patch.session.pk
    else:
        target_global_rev = global_revision
        target_session = session_id

    result_payload = get_latest_state(
        state_inst.agent,
        state_id=state_inst.pk,
        global_revision=target_global_rev,
        session_id=target_session,
        forward_patch_count=forward_patch_count,
    )

    if not result_payload or "states" not in result_payload or state_inst.interface not in result_payload["states"]:
        raise ObjectDoesNotExist(f"No state found for {state}")

    state_data = result_payload["states"][state_inst.interface]
    current_global_rev = state_data.get("global_revision")

    # Forward patches are now fetched by get_latest_state at the global agent level
    forward_patches = result_payload.get("forward_patches", [])

    return StateValue(
        state_id=state,
        value=state_data,
        global_revision=current_global_rev,
        forward_patches=forward_patches,
    )


@strawberry.type
class AgentWithValues:
    """An agent alongside all of its current state values."""

    agent_id: strawberry.ID = strawberry.field(description="The ID of the agent this state belongs to")
    values: strawberry.scalars.JSON = strawberry.field(description="The state value, indexed by state_interface")
    global_revision: int = strawberry.field(description="The maximum global revision across these states")
    forward_patches: List[types.Patch] = strawberry.field(description="The patches to move forward")


def checkout_agent(
    info: Info,
    agent: strawberry.ID,
    session_id: strawberry.ID | None = None,
    global_revision: int | None = None,
    timestamp: datetime.datetime | None = None,
    forward_patch_count: int = 0,
) -> AgentWithValues:
    """Checkout all states for a given agent at a specific revision."""
    agent_inst = models.Agent.objects.get(id=agent)

    if timestamp:
        latest_patch = models.Patch.objects.filter(agent=agent, timestamp__lte=timestamp).order_by("-timestamp").first()

        if not latest_patch:
            raise ObjectDoesNotExist(f"No patches found for state {agent} before timestamp {timestamp}")

        target_global_rev = latest_patch.global_rev
        target_session = latest_patch.session.session_id
    else:
        target_global_rev = global_revision
        target_session = session_id

    result_payload = (
        get_latest_state(
            agent_inst,
            global_revision=target_global_rev,
            session_id=target_session,
            forward_patch_count=forward_patch_count,
        )
        or {}
    )

    agent_values = {}
    result_map = result_payload.get("states", {})
    max_global_revision = result_payload.get("global_revision", 0)

    # Use the forward patches returned directly from the payload
    forward_patches = result_payload.get("forward_patches", [])

    return AgentWithValues(
        agent_id=agent_inst.pk,
        values=result_map,
        global_revision=max_global_revision,
        forward_patches=forward_patches,
    )
