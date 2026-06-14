import logging

from facade import models, types
from kante.types import Info
from authentikate.vars import get_user, get_client

logger = logging.getLogger(__name__)


def myreservations(
    info: Info,
) -> types.Action:
    registry, _ = models.Registry.objects.get_or_create(client=info.context.request.client, user=info.context.request.user, organization=info.context.request.organization)

    return models.Reservation.objects.filter(registry=registry).all


def reservations(
    info: Info,
) -> list[types.Reservation]:
    registry, _ = models.Registry.objects.get_or_create(client=info.context.request.client, user=info.context.request.user, organization=info.context.request.organization)

    return models.Reservation.objects.filter(registry=registry)
