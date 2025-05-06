from kante.types import Info
import strawberry
from facade import types, models
from typing import AsyncGenerator
from facade.channels import (
    state_update_channel,
)


async def state_update_events(
    self,
    info: Info,
    state_id: strawberry.ID,
) -> AsyncGenerator[types.State, None]:
    """Join and subscribe to message sent to the given rooms."""

    state = await models.State.objects.aget(id=state_id)

    async for message in state_update_channel.listen(
        info.context, [f"new_state_stuff{state.id}", "cactusfart"]
    ):
        yield await models.State.objects.aget(id=message)
