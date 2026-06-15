from kante.types import Info
import strawberry
from facade import types, models
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
) -> AsyncGenerator[types.Reservation, None]:
    """Join and subscribe to message sent to the given rooms."""

    user = info.context.request.user
    client = info.context.request.client

    caller, _ = await models.Caller.objects.aget_or_create(client=client, user=user, organization=info.context.request.organization)

    async for message in reservation_channel.listen(info.context, [f"res_caller_{caller.id}"]):
        continue
        yield await models.Reservation.objects.aget(id=message)
