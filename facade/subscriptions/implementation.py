from kante.types import Info
import strawberry_django
import strawberry
from facade import types, models
from typing import AsyncGenerator
from facade.channels import implementation_listen


@strawberry.type
class ImplementationUpdate:
    create: types.Implementation
    update: types.Implementation
    delete: strawberry.ID


async def implementations(
    self,
    info: Info,
    agent: strawberry.ID,
) -> AsyncGenerator[ImplementationUpdate, None]:
    """Join and subscribe to message sent to the given rooms."""
    async for message in implementation_listen(info, [f"agent_{agent}"]):
        if message["type"] == "create":
            yield await models.Implementation.objects.aget(id=message["id"])
        elif message["type"] == "update":
            yield await models.Implementation.objects.aget(id=message["id"])
        elif message["type"] == "delete":
            yield message["id"]


async def implementation_change(
    self,
    info: Info,
    implementation: strawberry.ID,
) -> AsyncGenerator[types.Implementation, None]:
    """Join and subscribe to message sent to the given rooms."""
    x = await models.Implementation.objects.aget(id=implementation)

    async for message in implementation_listen(info, [f"implementation_{x.id}"]):
        yield await models.Implementation.objects.aget(id=message)
