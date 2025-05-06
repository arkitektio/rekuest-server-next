from kante.types import Info
import strawberry
from facade import types, models
from typing import AsyncGenerator
from facade.channels import action_channel


async def new_actions(
    self,
    info: Info,
    cage: strawberry.ID,
) -> AsyncGenerator[types.Action, None]:
    """Join and subscribe to message sent to the given rooms."""
    async for message in action_channel.listen(info.context, ["actions"]):
        if message.create:
            yield await models.Action.objects.aget(id=message.create)
        if message.update:
            yield await models.Action.objects.aget(id=message.update)
       
