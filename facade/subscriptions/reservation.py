from kante.types import Info
import strawberry_django
import strawberry
from facade import types, models, scalars
from typing import AsyncGenerator
from facade.channels import (
    action_created_listen,
    reservation_event_listen,
    reservation_listen,
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

    registry, _ = await models.Registry.objects.aget_or_create(
        app=info.context.request.app, user=info.context.request.user
    )

    waiter, _ = await models.Waiter.objects.aget_or_create(
        registry=registry, instance_id=instance_id, defaults=dict(name="default")
    )

    async for message in reservation_listen(info, [f"res_waiter_{waiter.id}"]):
        continue
        yield await models.Reservation.objects.aget(id=message)
