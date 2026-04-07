from kante.types import Info
import strawberry
import datetime
from facade import types, models, scalars, enums
from typing import AsyncGenerator, Union
from facade.channels import (
    state_update_channel,
    patch_channel,
)


async def state_update_events(
    self,
    info: Info,
    state_id: strawberry.ID,
) -> AsyncGenerator[types.State, None]:
    """Join and subscribe to message sent to the given rooms."""

    state = await models.State.objects.aget(id=state_id)

    async for message in state_update_channel.listen(info.context, [f"state_{state.id}"]):
        yield await models.State.objects.aget(id=message.state)


async def latest_patches(
    self,
    info: Info,
    state: strawberry.ID | None = None,
    agent: strawberry.ID | None = None,
) -> AsyncGenerator[types.Patch, None]:
    """Watch for patch updates based on filters"""

    topics = []
    if state:
        topics.append(f"patches_state_{state}")
    elif agent:
        topics.append(f"patches_agent_{agent}")

    if not topics:
        return

    async for message in patch_channel.listen(info.context, topics):
        try:
            patch = await models.Patch.objects.select_related("state", "agent").aget(id=message.create)

            if state and str(patch.state.id) != str(state):
                continue
            if agent and (not patch.agent or str(patch.agent_id) != str(agent)):
                continue

            yield patch
        except models.Patch.DoesNotExist:
            continue


# Plain types for watch subscriptions (no model cross-references)


@strawberry.type(description="A plain snapshot of a state's current value.")
class StateSnapshotEvent:
    state_id: strawberry.ID
    agent_id: strawberry.ID
    interface: str
    value: scalars.Args
    global_revision: int
    session_id: str
    timestamp: datetime.datetime


@strawberry.type(description="A plain patch event with no model cross-references.")
class StatePatchEvent:
    state_id: strawberry.ID
    agent_id: strawberry.ID
    op: str
    path: str
    value: scalars.Args
    global_revision: int
    session_id: str
    timestamp: datetime.datetime


async def watch_state(
    self,
    info: Info,
    state_id: strawberry.ID | None = None,
    agent_id: strawberry.ID | None = None,
    interface: str | None = None,
) -> AsyncGenerator[StateSnapshotEvent | StatePatchEvent, None]:
    """Watch a state: yields the current snapshot then streams patches and state updates."""

    if state_id:
        state = await models.State.objects.select_related("agent").aget(id=state_id)
    else:
        state = await models.State.objects.select_related("agent").aget(
            agent_id=agent_id,
            interface=interface,
        )

    # Find the latest snapshot to determine global_revision
    latest_snapshot = await models.Snapshot.objects.filter(state=state).order_by("-global_rev").afirst()

    global_rev = latest_snapshot.global_rev if latest_snapshot else 0
    snapshot_value = latest_snapshot.value if latest_snapshot else state.value

    if not latest_snapshot:
        raise ValueError("State not found or has no snapshots yet.")

    yield StateSnapshotEvent(
        state_id=strawberry.ID(str(state.id)),
        agent_id=strawberry.ID(str(state.agent_id)),
        interface=state.interface,
        value=snapshot_value,
        global_revision=global_rev,
        session_id=latest_snapshot.session_id if latest_snapshot else None,
        timestamp=state.updated_at,
    )

    topics = [
        f"state_{state.id}",
        f"patches_state_{state.id}",
    ]

    print("Watching state with topics:", topics)

    async for message in patch_channel.listen(info.context, topics):
        try:
            patch = await models.Patch.objects.aget(id=message.create)
            yield StatePatchEvent(
                state_id=strawberry.ID(str(patch.state_id)),
                agent_id=strawberry.ID(str(patch.agent_id)) if patch.agent_id else strawberry.ID(""),
                op=patch.op,
                path=patch.path,
                value=patch.value,
                global_revision=patch.global_rev,
                session_id=patch.session_id,
                timestamp=patch.timestamp,
            )
        except models.Patch.DoesNotExist:
            continue


async def watch_agent(
    self,
    info: Info,
    agent_id: strawberry.ID,
) -> AsyncGenerator[StateSnapshotEvent | StatePatchEvent, None]:
    """Watch an agent: yields current snapshots for all states then streams patches and state updates."""

    agent = await models.Agent.objects.aget(id=agent_id)

    # Yield a snapshot for each state of this agent
    async for state in models.State.objects.filter(agent=agent):
        latest_snapshot = await models.Snapshot.objects.filter(state=state).order_by("-global_rev").afirst()

        global_rev = latest_snapshot.global_rev if latest_snapshot else 0
        snapshot_value = latest_snapshot.value if latest_snapshot else state.value

        yield StateSnapshotEvent(
            state_id=strawberry.ID(str(state.id)),
            agent_id=strawberry.ID(str(agent.id)),
            interface=state.interface,
            value=snapshot_value,
            global_revision=global_rev,
            timestamp=state.updated_at,
        )

    topics = [f"patches_agent_{agent.id}"]

    async for message in patch_channel.listen(info.context, topics):
        try:
            patch = await models.Patch.objects.aget(id=message.create)

            if not patch.agent_id or str(patch.agent_id) != str(agent.id):
                continue

            yield StatePatchEvent(
                state_id=strawberry.ID(str(patch.state_id)),
                agent_id=strawberry.ID(str(patch.agent_id)),
                op=patch.op,
                path=patch.path,
                value=patch.value,
                global_revision=patch.global_rev,
                session_id=patch.session_id,
                timestamp=patch.timestamp,
            )
        except models.Patch.DoesNotExist:
            continue
