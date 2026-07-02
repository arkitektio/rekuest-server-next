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
    task: strawberry.ID | None = None,
    implementation: strawberry.ID | None = None,
    agent: strawberry.ID | None = None,
    interface: str | None = None,
    hash: rscalars.ActionHash | None = None,
    matching: rinputs.ActionDemandInput | None = None,
) -> types.Action:
    if task:
        return models.Task.objects.get(id=task).action
    if implementation:
        return models.Implementation.objects.get(id=implementation).action

    if hash:
        return models.Action.objects.get(hash=hash, organization=info.context.request.organization)

    if matching:
        ids = managers.get_action_ids_by_action_demands(
            [matching],
            organization_id=info.context.request.organization.id,
        )[0]

        return models.Action.objects.get(id=ids[0])

    if agent:
        if interface:
            return models.Implementation.objects.filter(action__hash=hash, interface=interface).first().action
        else:
            raise ValueError("You need to provide either, action_hash or action_id, if you want to inspect the action of an agent")

    return models.Action.objects.get(id=id)
