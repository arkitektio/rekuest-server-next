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
    return controll_backend.reserve(info, input)


@strawberry.input
class UnreserveInput:
    reservation: strawberry.ID


def unreserve(info: Info, input: UnreserveInput) -> str:

    reservation = models.Reservation.objects.get(id=input.reservation)
    reservation.delete()

    return input.reservation


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
