from facade.enums import (
    AgentStatus,
    AssignationStatus,
    ProvisionStatus,
    ReservationStatus,
)
from facade import models
from asgiref.sync import sync_to_async
from .carrots import (
    AssignHareMessage,
    AssignationChangedHareMessage,
    ReservationChangedMessage,
    ReserveHareMessage,
    UnreserveHareMessage,
)
from . import messages
from .agent_json import *
import logging
from facade.utils import cascade_agent_failure

logger = logging.getLogger(__name__)


def cascade_agent_failure(agent: Agent, agent_status: AgentStatus):
    """Cascades agent failure to all reservations and provisions"""

    forwards = []
    for provision in agent.provisions.exclude(
        status__in=[ProvisionStatus.CANCELLED, ProvisionStatus.ENDED]
    ).all():
        provision.status = ProvisionStatus.DISCONNECTED
        provision.save()

        for res in provision.reservations.all():
            res_params = ReserveParams(**res.params)
            viable_provisions_amount = min(
                res_params.minimalInstances, res_params.desiredInstances
            )

            if (
                res.provisions.filter(status=ProvisionStatus.ACTIVE).count()
                < viable_provisions_amount
            ):
                res.status = ReservationStatus.DISCONNECT
                res.save()
                forwards += [
                    ReservationChangedMessage(
                        queue=res.waiter.queue,
                        reservation=res.id,
                        status=res.status,
                    )
                ]

    agent.status = agent_status
    agent.save()

    return forwards


def list_provisions(agent: models.Agent, **kwargs):
    reply = []

    provisions = models.Provision.objects.filter(agent=agent).exclude(
        status__in=[
            ProvisionStatus.CANCELLED,
        ]
    )

    provisions = [
        messages.Provision(
            provision=prov.id,
            guardian=prov.id,
            status=prov.status,
            implementation=prov.implementation.id,
        )
        for prov in provisions
    ]

    reply += [ProvisionListReply(provisions=provisions)]

    return reply


def list_assignations(agent: models.Agent, **kwargs):
    reply = []
    forward = []

    assignations = models.Assignation.objects.filter(provision__agent=agent).exclude(
        status__in=[
            AssignationStatus.RETURNED,
            AssignationStatus.CANCELING,
            AssignationStatus.CANCELLED,
            AssignationStatus.ACKNOWLEDGED,
            AssignationStatus.DONE,
            AssignationStatus.ERROR,
            AssignationStatus.CRITICAL,
        ]
    )
    assignations = []

    assignations = [
        messages.Assignation(
            assignation=ass.id,
            guardian=ass.id,
            status=ass.status,
            args=ass.args,
            reservation=ass.reservation.id,
            provision=ass.provision.id,
            user=ass.creator.id,
        )
        for ass in assignations
    ]

    reply += [AssignationsInquiry(assignations=assignations)]

    return reply


def bind_assignation(m: AssignHareMessage, prov: str, **kwargs):
    reply = []
    forward = []
    try:
        ass = models.Assignation.objects.get(id=m.assignation)
        ass.provision_id = prov
        ass.status = AssignationStatus.BOUND
        ass.save()

        reply += [
            AssignSubMessage(
                assignation=ass.id,
                guardian=ass.id,
                status=ass.status,
                args=ass.args,
                reservation=ass.reservation.id,
                provision=ass.provision.id,
                user=ass.creator.id,
            )
        ]

    except Exception as e:
        logger.error("bin assignation failure", exc_info=True)

    return reply, forward


def change_assignation(m: AssignationChangedMessage, agent: models.Agent):
    reply = []
    forward = []
    try:
        ass = models.Assignation.objects.get(id=m.assignation)
        ass.status = m.status if m.status is not None else ass.status
        ass.args = m.args if m.args is not None else ass.args
        ass.returns = m.returns if m.returns is not None else ass.returns
        ass.progress = m.progress if m.progress is not None else ass.progress
        ass.statusmessage = m.message if m.message is not None else ass.statusmessage
        ass.save()

        forward += [
            AssignationChangedHareMessage(
                queue=ass.reservation.waiter.queue,
                reservation=ass.reservation.id,
                provision=ass.provision.id,
                **m.dict(exclude={"provision", "reservation", "type"}),
            )
        ]

    except Exception as e:
        logger.error("chagne assignation failure", exc_info=True)

    return reply, forward


def change_provision(m: ProvisionChangedMessage, agent: models.Agent):
    reply = []
    forward = []
    try:
        provision = models.Provision.objects.get(id=m.provision)
        provision.status = m.status if m.status else provision.status
        provision.statusmessage = m.message if m.message else provision.statusmessage
        provision.mode = m.mode if m.mode else provision.mode  #
        provision.save()

        if provision.status == ProvisionStatus.CRITICAL:
            for res in provision.reservations.filter(status=ReservationStatus.ACTIVE):
                if res.provisions.filter(status=ProvisionStatus.ACTIVE).count() == 0:
                    res.status = ReservationStatus.DISCONNECT
                    res.save()
                    forward += [
                        ReservationChangedMessage(
                            queue=res.waiter.queue,
                            reservation=res.id,
                            status=res.status,
                        )
                    ]

        if provision.status == ProvisionStatus.CANCELLED:
            for res in provision.reservations.filter(status=ReservationStatus.ACTIVE):
                if res.provisions.filter(status=ProvisionStatus.ACTIVE).count() == 0:
                    res.status = ReservationStatus.CANCELLED
                    res.save()
                    forward += [
                        ReservationChangedMessage(
                            queue=res.waiter.queue,
                            reservation=res.id,
                            status=res.status,
                            message="We were cancelled because the provision was cancelled.",
                        )
                    ]

    except Exception:
        logger.error("change provision error", exc_info=True)

    return reply, forward


@sync_to_async
def accept_reservation(m: ReserveHareMessage, agent: models.Agent):
    """SHould accept a reserve Hare Message
    and if this reservation is viable cause it to get
    active"""
    reply = []
    forward = []
    reservation_queues = []
    try:
        res = models.Reservation.objects.get(id=m.reservation)

        if res.provisions.filter(status=ProvisionStatus.ACTIVE).count() > 0:
            res.status = ReservationStatus.ACTIVE
            res.save()
            forward += [
                ReservationChangedMessage(
                    queue=res.waiter.queue,
                    reservation=res.id,
                    status=res.status,
                )
            ]

        reservation_queues += [(res.id, res.queue)]

    except Exception:
        logger.error("accept reservation error", exc_info=True)

    return reply, forward, reservation_queues


@sync_to_async
def loose_reservation(m: UnreserveHareMessage, agent: models.Agent):
    """SHould accept a reserve Hare Message
    and if this reservation is viable cause it to get
    active"""
    reply = []
    forward = []
    deleted_queues = []
    try:
        prov = models.Provision.objects.get(id=m.provision)
        res = models.Reservation.objects.get(id=m.reservation)
        prov.reservations.remove(res)

        if prov.reservations.count() == 0:
            reply += [
                UnprovideSubMessage(
                    provision=prov.id,
                    message=f"Was cancelled because last remaining reservation was cancelled {res}",
                )
            ]

        prov.save()
        deleted_queues += [res.id]

    except Exception:
        logger.error("loose reservation error", exc_info=True)

    return reply, forward, deleted_queues


@sync_to_async
def activate_provision(m: ProvisionChangedMessage, agent: models.Agent):
    reply = []
    forward = []
    reservation_queues = []
    assert m.status == ProvisionStatus.ACTIVE

    try:
        provision = models.Provision.objects.get(id=m.provision)
        provision.status = m.status if m.status else provision.status
        provision.statusmessage = m.message if m.message else provision.statusmessage
        provision.mode = m.mode if m.mode else provision.mode  #
        provision_queue = (str(provision.id), provision.queue)
        provision.save()

        for res in provision.reservations.filter():
            if res.provisions.filter(status=ProvisionStatus.ACTIVE).count() > 0:
                res.status = ReservationStatus.ACTIVE
                res.save()
                forward += [
                    ReservationChangedMessage(
                        queue=res.waiter.queue,
                        reservation=res.id,
                        status=res.status,
                    )
                ]

            reservation_queues += [(res.id, res.queue)]

        return reply, forward, reservation_queues, provision_queue

    except Exception:
        logger.error("active provision failure", exc_info=True)


@sync_to_async
def disconnect_agent(agent: models.Agent, close_code: int):
    return cascade_agent_failure(agent, AgentStatus.DISCONNECTED)


@sync_to_async
def log_to_provision(message: ProvisionLogMessage, agent: models.Agent):
    logging.info("log to provision {message}")
    models.ProvisionLog.objects.create(
        provision_id=message.provision, message=message.message, level=message.level
    )


@sync_to_async
def log_to_assignation(message: AssignationLogMessage, agent: models.Agent):
    models.AssignationLog.objects.create(
        assignation_id=message.assignation, message=message.message, level=message.level
    )
