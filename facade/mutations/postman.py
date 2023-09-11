from kante.types import Info
import strawberry_django
import strawberry
from facade import types, models, inputs, enums, scalars
import hashlib
import json
import logging
from facade.protocol import infer_protocols
from facade.utils import hash_input
from facade.logic import schedule_reservation
logger = logging.getLogger(__name__)
from facade.connection import redis_pool
import redis 

@strawberry.input
class ReserveInput:
    instance_id: scalars.InstanceID
    node: strawberry.ID | None = None
    template: strawberry.ID | None = None
    title: str | None = None
    hash: scalars.NodeHash | None = None
    provision: strawberry.ID | None = None
    reference: str | None = None
    binds: inputs.BindsInput | None = None


def reserve(info: Info, input: ReserveInput) -> types.Reservation:
    reference = input.reference or hash_input(
        input.binds or inputs.BindsInput(templates=[])
    )

    registry, _ = models.Registry.objects.get_or_create(
        app=info.context.request.app, user=info.context.request.user
    )
        

    waiter, _ = models.Waiter.objects.get_or_create(registry=registry, instance_id=input.instance_id , defaults=dict(name="default"))

    res, _ = models.Reservation.objects.update_or_create(
        reference=reference,
        node_id = input.node,
        waiter=waiter,
        defaults=dict(
            title=input.title,
            binds=strawberry.asdict(input.binds) if input.binds else None,
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
    r.lpush('my_queue', "task_data")



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
