import hashlib
import json
import logging

import strawberry
import strawberry_django
from kante.types import Info

from facade import enums, inputs, models, scalars, types
from facade.protocol import infer_protocols
from facade.utils import hash_input
from rekuest_core import scalars as rscalars

logger = logging.getLogger(__name__)


def node(
    info: Info,
    id: strawberry.ID | None = None,
    reservation: strawberry.ID | None = None,
    assignation: strawberry.ID | None = None,
    template: strawberry.ID | None = None,
    agent: strawberry.ID | None = None,
    interface: str | None = None,
    hash: rscalars.NodeHash | None = None,
) -> types.Node:
    if reservation:
        return models.Reservation.objects.get(id=reservation).node
    if assignation:
        return models.Assignation.objects.get(id=assignation).reservation.node
    if template:
        return models.Template.objects.get(id=template).node

    if hash:
        return models.Node.objects.get(hash=hash)

    if agent:
        if interface:
            return (
                models.Template.objects.filter(node__hash=hash, interface=interface)
                .first()
                .node
            )
        else:
            raise ValueError(
                "You need to provide either, node_hash or node_id, if you want to inspect the node of an agent"
            )

    return models.Node.objects.get(id=id)
