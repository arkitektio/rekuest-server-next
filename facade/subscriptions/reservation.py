from kante.types import Info
import strawberry
from facade import types, models, scalars
from typing import AsyncGenerator
from facade.channels import (
    reservation_channel,
)


@strawberry.type
class ReservationSubscription:
    create: types.Reservation
    delete: strawberry.ID


async def reservations(
    self,
    info: Info,
    instance_id: scalars.InstanceID,
) -> AsyncGenerator[types.Reservation, None]:
    """Join and subscribe to message sent to the given rooms."""

    user = info.context.request.user
    client = info.context.request.client

    registry, _ = await models.Registry.objects.aget_or_create(client=client, user=user)

    waiter, _ = await models.Waiter.objects.aget_or_create(
        registry=registry, instance_id=instance_id, defaults=dict(name="default")
    )

    async for message in reservation_channel.listen(
        info.context, [f"res_waiter_{waiter.id}"]
    ):
        continue
        yield await models.Reservation.objects.aget(id=message)
