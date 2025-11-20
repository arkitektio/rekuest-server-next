import logging

import strawberry
from kante.types import Info
from rekuest_core import scalars as rscalars
from rekuest_core.inputs import types as rinputs
from facade import models, types, managers

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
    matching: rinputs.ActionDependencyInput | None = None,
) -> types.Action:
    if reservation:
        return models.Reservation.objects.get(id=reservation).action
    if assignation:
        return models.Assignation.objects.get(id=assignation).reservation.action
    if implementation:
        return models.Implementation.objects.get(id=implementation).action

    if hash:
        return models.Action.objects.get(hash=hash, organization=info.context.request.organization)

    if matching:
        ids = managers.get_action_ids_by_action_demand(
            matching,
            model="facade_action",
            organization_id=info.context.request.organization.id,
        )

        return models.Action.objects.get(id=ids[0])

    if agent:
        if interface:
            return models.Implementation.objects.filter(action__hash=hash, interface=interface).first().action
        else:
            raise ValueError("You need to provide either, action_hash or action_id, if you want to inspect the action of an agent")

    return models.Action.objects.get(id=id)
