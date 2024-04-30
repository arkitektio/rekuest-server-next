from kante.types import Info
import strawberry_django
import strawberry
from facade import types, models
from typing import AsyncGenerator
from facade.channels import agent_updated_listen




async def agents(
    self,
    info: Info,
    cage: strawberry.ID,
) -> AsyncGenerator[types.Agent, None]:
    """Join and subscribe to message sent to the given rooms."""
    async for message in agent_updated_listen(info, [f"agents"]):
        yield await models.Agent.objects.aget(id=message)