from kante.types import Info
import strawberry
import datetime
from facade import types, models, scalars, enums, logic
from typing import AsyncGenerator, Union
from facade.channels import (
    state_update_channel,
    patch_channel,
)
from asgiref.sync import sync_to_async


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
    interface: str
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

    returned = await sync_to_async(logic.get_latest_state)(state.agent, state_id=state.id)

    yield StateSnapshotEvent(
        state_id=strawberry.ID(str(state_id)),
        agent_id=strawberry.ID(str(state.agent_id)),
        interface=state.interface,
        value=returned.get("states", {}).get(state.interface),
        global_revision=returned.get("global_revision", 0),
        session_id=returned.get("session_id"),
        timestamp=returned.get("timestamp"),
    )

    topics = [
        f"state_{state.id}",
        f"patches_state_{state.id}",
    ]

    async for message in patch_channel.listen(info.context, topics):
        # TODO: optimize by NOT using a model here but sending the raw patch data in the channel message (from the agent to this receiver)
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
                interface=patch.interface,
            )
        except models.Patch.DoesNotExist:
            continue


@strawberry.type(description="A plain snapshot of a state's current value.")
class AgentSnapshotEvent:
    agent_id: strawberry.ID
    values: scalars.Args
    global_revision: int
    session_id: str
    timestamp: datetime.datetime


async def watch_agent(
    self,
    info: Info,
    agent_id: strawberry.ID,
) -> AsyncGenerator[AgentSnapshotEvent | StatePatchEvent, None]:
    """Watch an agent: yields current snapshots for all states then streams patches and state updates."""

    agent = await models.Agent.objects.aget(id=agent_id)

    # Yield a snapshot for each state of this agent
    state = await sync_to_async(logic.get_latest_state)(agent)

    topics = [f"patches_agent_{agent.pk}"]

    yield AgentSnapshotEvent(
        agent_id=strawberry.ID(str(agent.id)),
        values=state.get("states", {}),
        global_revision=state.get("global_revision", 0),
        session_id=state.get("session_id"),
        timestamp=state.get("timestamp"),
    )

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
                interface=patch.interface,
            )
        except models.Patch.DoesNotExist:
            continue
