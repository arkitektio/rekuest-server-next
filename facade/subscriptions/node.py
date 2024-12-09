from kante.types import Info
import strawberry_django
import strawberry
from facade import types, models
from typing import AsyncGenerator
from facade.channels import node_created_listen


async def new_nodes(
    self,
    info: Info,
    cage: strawberry.ID,
) -> AsyncGenerator[types.Node, None]:
    """Join and subscribe to message sent to the given rooms."""
    async for message in node_created_listen(info, [f"nodes"]):
        yield await models.Node.objects.aget(id=message)
