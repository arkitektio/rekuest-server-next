from kante.types import Info
import strawberry_django
import strawberry
from facade import types, models, scalars
from typing import AsyncGenerator
from facade.channels import node_created_listen


async def reservations(
    self,
    info: Info,
    instance_id: scalars.InstanceID,
) -> AsyncGenerator[types.ReservationEvent, None]:
    """Join and subscribe to message sent to the given rooms."""
    async for message in node_created_listen(info, [f"nodes"]):
        yield await models.ReservationEvent.objects.aget(id=message)
