import logging

import strawberry
from kante.types import Info
from rekuest_core import scalars as rscalars

from facade import models, types

logger = logging.getLogger(__name__)


def action(
    info: Info,
    id: strawberry.ID | None = None,
    reservation: strawberry.ID | None = None,
    assignation: strawberry.ID | None = None,
    implementation: strawberry.ID | None = None,
    agent: strawberry.ID | None = None,
    interface: str | None = None,
    hash: rscalars.ActionHash | None = None,
) -> types.Action:
    if reservation:
        return models.Reservation.objects.get(id=reservation).action
    if assignation:
        return models.Assignation.objects.get(id=assignation).reservation.action
    if implementation:
        return models.Implementation.objects.get(id=implementation).action

    if hash:
        return models.Action.objects.get(hash=hash)

    if agent:
        if interface:
            return (
                models.Implementation.objects.filter(
                    action__hash=hash, interface=interface
                )
                .first()
                .action
            )
        else:
            raise ValueError(
                "You need to provide either, action_hash or action_id, if you want to inspect the action of an agent"
            )

    return models.Action.objects.get(id=id)
