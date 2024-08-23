from kante.types import Info
import strawberry_django
import strawberry
from facade import types, models, scalars, enums
from typing import AsyncGenerator, Optional
from facade.channels import node_created_listen, state_update_event_listen, assignation_listen



async def state_update_events(
    self,
    info: Info,
    state_id: strawberry.ID,
) -> AsyncGenerator[types.StateUpdateEvent, None]:
    """Join and subscribe to message sent to the given rooms."""

    print(info)

    state = await models.State.objects.aget(id=state_id)

    async for message in state_update_event_listen(info, [f"state_{state.id}"]):
        yield message


