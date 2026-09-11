from kante.types import Info
import strawberry
from facade import types, models
from typing import AsyncGenerator, Optional
from facade.channels import new_implementation_channel


@strawberry.type(description="An implementation feed event: exactly one of create/update/delete is set.")
class ImplementationUpdate:
    create: Optional[types.Implementation] = None
    update: Optional[types.Implementation] = None
    delete: Optional[strawberry.ID] = None


async def implementations(
    self,
    info: Info,
    agent: strawberry.ID,
) -> AsyncGenerator[ImplementationUpdate, None]:
    """Subscribe to implementation create/update/delete for one agent."""
    async for message in new_implementation_channel.listen(info.context, [f"implementations_agent_{agent}"]):
        if message.create:
            yield ImplementationUpdate(create=await models.Implementation.objects.aget(id=message.create))
        elif message.update:
            yield ImplementationUpdate(update=await models.Implementation.objects.aget(id=message.update))
        elif message.delete:
            yield ImplementationUpdate(delete=strawberry.ID(str(message.delete)))


async def implementation_change(
    self,
    info: Info,
    implementation: strawberry.ID,
) -> AsyncGenerator[types.Implementation, None]:
    """Subscribe to updates of one implementation."""
    x = await models.Implementation.objects.aget(id=implementation)

    async for message in new_implementation_channel.listen(info.context, [f"implementation_{x.id}"]):
        # Deletes end the row — nothing to yield for this row-typed stream.
        if message.update:
            yield await models.Implementation.objects.aget(id=message.update)
