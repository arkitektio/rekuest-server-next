import logging

from facade import models, scalars, types
from kante.types import Info
from authentikate.vars import get_user, get_client

logger = logging.getLogger(__name__)


def myreservations(
    info: Info,
    instance_id: scalars.InstanceID | None = None,
) -> types.Action:
    registry, _ = models.Registry.objects.get_or_create(
        client=info.context.request.client, user=info.context.request.user
    )

    waiter, _ = models.Waiter.objects.get_or_create(
        registry=registry, instance_id=instance_id, defaults=dict(name="default")
    )

    return models.Reservation.objects.filter(waiter=waiter).all


def reservations(
    info: Info,
    instance_id: scalars.InstanceID | None = None,
) -> list[types.Reservation]:
  
    registry, _ = models.Registry.objects.get_or_create(
        client=info.context.request.client, user=info.context.request.user
    )

    waiter, _ = models.Waiter.objects.get_or_create(
        registry=registry, instance_id=instance_id, defaults=dict(name="default")
    )

    return models.Reservation.objects.filter(waiter=waiter)
