import logging

from facade.backend import controll_backend
import strawberry
from facade import inputs, models, types
from kante.types import Info

logger = logging.getLogger(__name__)


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


def collect(info: Info, input: inputs.CollectInput) -> list[str]:
    return controll_backend.collect(info, input)
