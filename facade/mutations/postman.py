from kante.types import Info
import strawberry_django
import strawberry
from facade import types, models, inputs, enums, scalars
from rekuest_core.inputs import models as rimodels
import hashlib
import json
import logging
from facade.protocol import infer_protocols
from facade.utils import hash_input
from facade.logic import schedule_reservation

logger = logging.getLogger(__name__)
from facade.connection import redis_pool
import redis


def reserve(info: Info, input: inputs.ReserveInput) -> types.Reservation:
    if (input.node is None and input.template is None):
        raise ValueError("Either node or template must be provided")

    node = models.Node.objects.get(hash=input.node) if input.node else None
    template = models.Template.objects.get(id=input.template) if input.template else None


    reference = input.reference or hash_input(
        input.binds or rimodels.BindsInputModel(templates=[])
    )

    registry, _ = models.Registry.objects.get_or_create(
        app=info.context.request.app, user=info.context.request.user
    )

    waiter, _ = models.Waiter.objects.get_or_create(
        registry=registry, instance_id=input.instance_id, defaults=dict(name="default")
    )



    res, _ = models.Reservation.objects.update_or_create(
        reference=reference,
        node=node,
        template=template,
        waiter=waiter,
        defaults=dict(
            title=input.title,
            binds=input.binds.dict() if input.binds else None,
        ),
    )

    schedule_reservation(res)

    return res


@strawberry.input
class UnreserveInput:
    reservation: strawberry.ID


def unreserve(info: Info, input: UnreserveInput) -> types.Reservation:
    return models.Reservation.objects.get(id=input.reservation)


@strawberry.input
class AssignInput:
    reservation: strawberry.ID
    args: list[scalars.Arg]
    reference: str | None = None
    parent: strawberry.ID | None = None


def assign(info: Info, input: AssignInput) -> types.Assignation:
    r = redis.StrictRedis(connection_pool=redis_pool)
    r.lpush("my_queue", "task_data")


@strawberry.input
class AckInput:
    assignation: strawberry.ID


def ack(info: Info, input: AckInput) -> types.Assignation:
    return models.Assignation.objects.get(id=input.id)


@strawberry.input
class UnassignInput:
    assignation: strawberry.ID


def unassign(info: Info, input: UnassignInput) -> types.Assignation:
    return models.Assignation.objects.get(id=input.id)
