from kante.types import Info
import strawberry_django
import strawberry
from facade import types, models
from typing import AsyncGenerator
from facade.channels import action_created_listen


async def new_actions(
    self,
    info: Info,
    cage: strawberry.ID,
) -> AsyncGenerator[types.Action, None]:
    """Join and subscribe to message sent to the given rooms."""
    async for message in action_created_listen(info, [f"actions"]):
        yield await models.Action.objects.aget(id=message)
