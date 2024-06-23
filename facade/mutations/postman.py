import hashlib
import json
import logging

import strawberry
import strawberry_django
from facade import enums, inputs, models, scalars, types
from facade.logic import link as link_provision_to_reservation
from facade.logic import schedule_provision, schedule_reservation
from facade.logic import unlink as unlink_provision_from_reservation
from facade.protocol import infer_protocols
from facade.utils import hash_input
from kante.types import Info
from rekuest_core.inputs import models as rimodels

logger = logging.getLogger(__name__)
import redis
from facade.backend import controll_backend
from facade.connection import redis_pool


def reserve(info: Info, input: inputs.ReserveInput) -> types.Reservation:
    if input.node is None and input.template is None:
        raise ValueError("Either node or template must be provided")

    node = models.Node.objects.get(hash=input.node) if input.node else None
    template = (
        models.Template.objects.get(id=input.template) if input.template else None
    )

    reference = input.reference or hash_input(
        input.binds or rimodels.BindsInputModel(templates=[])
    )

    registry, _ = models.Registry.objects.get_or_create(
        app=info.context.request.app, user=info.context.request.user
    )

    waiter, _ = models.Waiter.objects.get_or_create(
        registry=registry, instance_id=input.instance_id, defaults=dict(name="default")
    )

    res, created = models.Reservation.objects.update_or_create(
        reference=reference,
        node=node or template.node,
        template=template,
        strategy=(
            enums.ReservationStrategy.DIRECT
            if template
            else enums.ReservationStrategy.ROUND_ROBIN
        ),
        waiter=waiter,
        defaults=dict(
            title=input.title,
            binds=input.binds.dict() if input.binds else None,
        ),
    )

    schedule_reservation(res)

    if created:
        models.ReservationEvent.objects.create(
            reservation=res,
            kind=enums.ReservationEventKind.PENDING,
            message="Created",
        )
    else:
        models.ReservationEvent.objects.create(
            reservation=res,
            kind=enums.ReservationEventKind.RESCHEDULE,
            message="Recreated",
        )

    return res


@strawberry.input
class UnreserveInput:
    reservation: strawberry.ID


def unreserve(info: Info, input: UnreserveInput) -> types.Reservation:

    reservation = models.Reservation.objects.get(id=input.reservation)
    reservation.delete()

    return models.Reservation.objects.get(id=input.reservation)


def assign(info: Info, input: inputs.AssignInput) -> types.Assignation:
    return controll_backend.assign(info, input)


@strawberry.input
class AckInput:
    assignation: strawberry.ID


def ack(info: Info, input: AckInput) -> types.Assignation:
    return models.Assignation.objects.get(id=input.id)


def cancel(info: Info, input: inputs.CancelInput) -> types.Assignation:
    return controll_backend.cancel(input)


def interrupt(info: Info, input: inputs.InterruptInput) -> types.Assignation:
    return controll_backend.interrupt(input)


@strawberry.input
class ProvideInput:
    provision: strawberry.ID


def provide(info: Info, input: ProvideInput) -> types.Provision:

    provision = models.Provision.objects.get(id=input.provision)

    schedule_provision(provision)

    return provision


@strawberry.input
class UnProvideInput:
    provision: strawberry.ID


def unprovide(info: Info, input: UnProvideInput) -> strawberry.ID:

    provision = models.Provision.objects.get(id=input.provision)

    return input.provision


@strawberry.input
class LinkInput:
    provision: strawberry.ID
    reservation: strawberry.ID


def link(info: Info, input: LinkInput) -> types.Provision:
    provision = models.Provision.objects.get(id=input.provision)
    reservation = models.Reservation.objects.get(id=input.reservation)

    link_provision_to_reservation(provision, reservation)

    return provision


@strawberry.input
class UnlinkInput:
    provision: strawberry.ID
    reservation: strawberry.ID


def unlink(info: Info, input: UnlinkInput) -> types.Provision:
    provision = models.Provision.objects.get(id=input.provision)
    reservation = models.Reservation.objects.get(id=input.reservation)

    unlink_provision_from_reservation(provision, reservation)

    return provision
