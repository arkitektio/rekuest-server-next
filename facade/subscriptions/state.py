from kante.types import Info
import strawberry_django
import strawberry
from facade import types, models, scalars, enums
from typing import AsyncGenerator, Optional
from facade.channels import (
    node_created_listen,
    state_update_event_listen,
    assignation_listen,
    new_state_listen,
)


async def state_update_events(
    self,
    info: Info,
    state_id: strawberry.ID,
) -> AsyncGenerator[types.State, None]:
    """Join and subscribe to message sent to the given rooms."""

    state = await models.State.objects.aget(id=state_id)

    async for message in new_state_listen(
        info, [f"new_state_stuff{state.id}", "cactusfart"]
    ):
        yield await models.State.objects.aget(id=message)
