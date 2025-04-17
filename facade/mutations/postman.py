
import logging

import strawberry
from facade import enums, inputs, models, scalars, types
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



def pause(info: Info, input: inputs.PauseInput) -> types.Assignation:
    return controll_backend.pause(input)


def resume(info: Info, input: inputs.ResumeInput) -> types.Assignation:
    return controll_backend.resume(input)

def collect(info: Info, input: inputs.CollectInput) -> types.Assignation:
    return controll_backend.resume(input)


def step(info: Info, input: inputs.StepInput) -> types.Assignation:
    return controll_backend.step(input)


@strawberry.input
class AckInput:
    assignation: strawberry.ID


def ack(info: Info, input: AckInput) -> types.Assignation:
    return models.Assignation.objects.get(id=input.id)


def cancel(info: Info, input: inputs.CancelInput) -> types.Assignation:
    return controll_backend.cancel(input)


def interrupt(info: Info, input: inputs.InterruptInput) -> types.Assignation:
    return controll_backend.interrupt(input)


