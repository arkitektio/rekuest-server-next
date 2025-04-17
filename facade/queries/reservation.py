import hashlib
import json
import logging

import strawberry
import strawberry_django
from facade import enums, inputs, models, scalars, types
from facade.protocol import infer_protocols
from facade.utils import hash_input
from kante.types import Info

logger = logging.getLogger(__name__)


def myreservations(
    info: Info,
    instance_id: scalars.InstanceID | None = None,
) -> types.Node:
    registry, _ = models.Registry.objects.get_or_create(
        app=info.context.request.app, user=info.context.request.user
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
        app=info.context.request.app, user=info.context.request.user
    )

    waiter, _ = models.Waiter.objects.get_or_create(
        registry=registry, instance_id=instance_id, defaults=dict(name="default")
    )

    return models.Reservation.objects.filter(waiter=waiter)
