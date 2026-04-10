from facade import models, types, inputs, managers
from kante.types import Info
import strawberry
from facade.logic import get_latest_state
from django.db.models import Min, Max, Q
from typing import Optional, List, cast
import datetime
import jsonpatch  # type: ignore[import-untyped]
from django.core.exceptions import ObjectDoesNotExist


def state_for(
    info: Info,
    agent: strawberry.ID,
    state_hash: str | None = None,
    demand: inputs.SchemaDemandInput | None = None,
) -> types.State:
    """Get a state for an agent."""
    agent = models.Agent.objects.get(id=agent)

    if demand:
        if demand.matches:
            state_ids = managers.get_state_ids_by_demands(demand.matches)

        return models.State.objects.get(agent=agent, id__in=state_ids)

    if state_hash:
        return models.State.objects.get(agent=agent, state_schema__hash=state_hash)

    raise ValueError("Either state_hash or demand must be provided")


def task_boundaries(
    info: Info,
    correlation_id: str,
    state_id: strawberry.ID | None = None,
) -> Optional[types.TaskBoundary]:
    queryset = models.Patch.objects.filter(assignation__reference=correlation_id)
    if state_id:
        queryset = queryset.filter(state_id=state_id)

    agg = queryset.aggregate(
        start_global_revision=Min("global_current_revision"),
        end_global_revision=Max("global_future_revision"),
        start_time=Min("timestamp"),
        end_time=Max("timestamp"),
    )

    if agg["start_global_revision"] is None:
        return None

    return types.TaskBoundary(
        correlation_id=correlation_id,
        start_global_revision=agg["start_global_revision"],
        end_global_revision=agg["end_global_revision"],
        start_time=agg["start_time"],
        end_time=agg["end_time"],
    )


def session_boundaries(
    info: Info,
    session_id: strawberry.ID,
    state_id: strawberry.ID | None = None,
) -> Optional[types.SessionBoundary]:
    session = models.Session.objects.get(session_id=session_id)

    queryset = models.Patch.objects.filter(session=session_id)
    if state_id:
        queryset = queryset.filter(state_id=state_id)

    agg = queryset.aggregate(
        start_global_revision=Min("global_current_revision"),
        end_global_revision=Max("global_future_revision"),
        start_time=Min("timestamp"),
        end_time=Max("timestamp"),
    )

    if agg["start_global_revision"] is None:
        return None

    return types.SessionBoundary(
        session_id=session_id,
        start_global_revision=agg["start_global_revision"],
        end_global_revision=agg["end_global_revision"],
        start_time=agg["start_time"],
        end_time=agg["end_time"],
    )


def _get_state_ids(session_id: str | None) -> List[str]:
    # Logic to get distinct state_ids
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
) -> types.Snapshot | None:
    snapshot_revision_field = "global_revision" if use_global_revision else "revision"
    patch_current_field = "global_current_revision" if use_global_revision else "current_revision"
    patch_future_field = "global_future_revision" if use_global_revision else "future_revision"

    snapshot_qs = models.Snapshot.objects.filter(state_id=state_id)
    if session_id:
        snapshot_qs = snapshot_qs.filter(session_id=session_id)

    anchor_snapshot = snapshot_qs.filter(**{f"{snapshot_revision_field}__lte": target_revision}).order_by(f"-{snapshot_revision_field}").first()

    if not anchor_snapshot:
        return None

    patch_start_rev = getattr(anchor_snapshot, snapshot_revision_field) or 0

    patch_qs = models.Patch.objects.filter(state_id=state_id)
    if session_id:
        patch_qs = patch_qs.filter(session_id=session_id)

    patch_qs = patch_qs.filter(**{f"{patch_current_field}__gte": patch_start_rev, f"{patch_future_field}__lte": target_revision}).order_by(patch_current_field)

    state_data = anchor_snapshot.value
    last_snapshot = anchor_snapshot

    for patch in patch_qs:
        patch_doc = {"op": patch.op, "path": patch.path, "value": patch.value}
        if patch.op == "remove":
            patch_doc.pop("value", None)

        state_data = jsonpatch.apply_patch(state_data, [patch_doc], in_place=False)

        last_snapshot = types.Snapshot(value=state_data, timestamp=patch.timestamp, revision=patch.future_revision, global_revision=patch.global_future_revision, session_id=patch.session_id, state=patch.state)

    return last_snapshot


def state_at_global_rev(
    info: Info,
    global_revision: int,
    state_id: strawberry.ID | None = None,
    session_id: str | None = None,
) -> List[types.Snapshot]:
    if state_id is None:
        state_ids = _get_state_ids(session_id)
        results = []
        for sid in state_ids:
            res = _get_state_at_revision(global_revision, str(sid), session_id, use_global_revision=True)
            if res:
                results.append(res)
        return results
    else:
        res = _get_state_at_revision(global_revision, str(state_id), session_id, use_global_revision=True)
        return [res] if res else []


def state_at_local_rev(
    info: Info,
    revision: int,
    state_id: strawberry.ID | None = None,
    session_id: str | None = None,
) -> List[types.Snapshot]:
    if state_id is None:
        state_ids = _get_state_ids(session_id)
        results = []
        for sid in state_ids:
            res = _get_state_at_revision(revision, str(sid), session_id, use_global_revision=False)
            if res:
                results.append(res)
        return results
    else:
        res = _get_state_at_revision(revision, str(state_id), session_id, use_global_revision=False)
        return [res] if res else []


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

    queryset = queryset.order_by("global_current_revision", "state_id", "current_revision")[:count]
    return list(queryset)


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

    queryset = queryset.order_by("global_current_revision", "state_id", "current_revision")
    return list(queryset)


def snapshots_around_rev(
    info: Info,
    revision: int,
    state_id: strawberry.ID | None = None,
    session_id: str | None = None,
    before: int = 1,
    after: int = 1,
) -> List[types.Snapshot]:
    # Need to iterate over state_ids if None provided
    target_state_ids = [str(state_id)] if state_id else _get_state_ids(session_id)

    collected: List[types.Snapshot] = []

    for sid in target_state_ids:
        qs_before = models.Snapshot.objects.filter(state_id=sid, revision__lte=revision)
        if session_id:
            qs_before = qs_before.filter(session_id=session_id)
        qs_before = qs_before.order_by("-revision")[:before]

        qs_after = models.Snapshot.objects.filter(state_id=sid, revision__gt=revision)
        if session_id:
            qs_after = qs_after.filter(session_id=session_id)
        qs_after = qs_after.order_by("revision")[:after]

        before_list = list(reversed(list(qs_before)))
        after_list = list(qs_after)

        collected.extend(before_list + after_list)

    return collected


@strawberry.type
class StateWithValue:
    """A state value and its schema."""

    value: strawberry.scalars.JSON
    definition: types.StateDefinition
    global_revision: int | None = None
    local_revision: int | None = None


def checkout(
    info: Info,
    state: strawberry.ID,
    session_id: strawberry.ID | None = None,
    global_revision: int | None = None,
    timestamp: datetime.datetime | None = None,
) -> StateWithValue:
    """Checkout a state at a specific revision."""
    state_inst = models.State.objects.get(id=state)

    if timestamp and global_revision:
        raise ValueError("Cannot specify both timestamp and global_revision")

    if global_revision:
        if session_id is None:
            latest_session = models.Session.objects.filter(agent=state_inst.agent).order_by("-created_at").first()
            if not latest_session:
                raise ObjectDoesNotExist(f"No sessions found for agent {state_inst.agent}")
            session_id = latest_session.session_id

        result = get_latest_state(
            state_inst.agent,
            state_id=state_inst.pk,
            global_revision=global_revision,
            session_id=session_id,
        )

    elif timestamp:
        latest_patch = models.Patch.objects.filter(state_id=state, agent=state_inst.agent, timestamp__lte=timestamp, session_id=session_id).order_by("-timestamp").first()
        if not latest_patch:
            raise ObjectDoesNotExist(f"No patches found for state {state} before timestamp {timestamp}")

        result = get_latest_state(
            state_inst.agent,
            state_id=state_inst.pk,
            global_revision=latest_patch.global_rev,
            session_id=latest_patch.session.pk,
        )

    else:
        raise ValueError("Must specify either global_revision or timestamp")

    if not result:
        raise ObjectDoesNotExist(f"No state found for {state}")

    key = list(result.keys())[0]
    return StateWithValue(
        value={str(k): v for k, v in result[key]["value"].items()},
        definition=result[key]["definition"],
        global_revision=result[key].get("global_revision"),
    )


def checkout_agent(
    info: Info,
    agent: strawberry.ID,
    session_id: strawberry.ID | None = None,
    global_revision: int | None = None,
    timestamp: datetime.datetime | None = None,
) -> List[StateWithValue]:
    """Checkout a state at a specific revision."""
    agent = models.Agent.objects.get(id=agent)

    states = []

    for state in models.State.objects.filter(agent=agent):
        state_inst = state

        try:
            if timestamp and global_revision:
                raise ValueError("Cannot specify both timestamp and global_revision")

            if global_revision:
                if session_id is None:
                    latest_session = models.Session.objects.filter(agent=state_inst.agent).order_by("-created_at").first()
                    if not latest_session:
                        raise ObjectDoesNotExist(f"No sessions found for agent {state_inst.agent}")
                    session_id = latest_session.session_id

                result = get_latest_state(
                    state_inst.agent,
                    state_id=state_inst.pk,
                    global_revision=global_revision,
                    session_id=session_id,
                )

            elif timestamp:
                latest_patch = models.Patch.objects.filter(state_id=state, agent=state_inst.agent, timestamp__lte=timestamp, session_id=session_id).order_by("-timestamp").first()
                if not latest_patch:
                    raise ObjectDoesNotExist(f"No patches found for state {state} before timestamp {timestamp}")

                result = get_latest_state(
                    state_inst.agent,
                    state_id=state_inst.pk,
                    global_revision=latest_patch.global_rev,
                    session_id=latest_patch.session.pk,
                )

            else:
                raise ValueError("Must specify either global_revision or timestamp")

            if not result:
                raise ObjectDoesNotExist(f"No state found for {state}")

            key = list(result.keys())[0]
            states.append(
                StateWithValue(
                    value={str(k): v for k, v in result[key]["value"].items()},
                    definition=result[key]["definition"],
                    global_revision=result[key].get("global_revision"),
                )
            )
        except Exception as e:
            print(f"Error checking out state {state}: {e}")
            continue

    return states
