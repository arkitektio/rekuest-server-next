from kante.types import Info
import strawberry
from facade import types, models
from typing import AsyncGenerator
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
