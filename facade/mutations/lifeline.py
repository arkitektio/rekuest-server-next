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
from facade.consumers.async_consumer import AgentConsumer

logger = logging.getLogger(__name__)
from facade.connection import redis_pool
import redis
from facade.backend import controll_backend
from facade.persist_backend import persist_backend


@strawberry.input
class ActivateInput:
    provision: strawberry.ID


def activate(info: Info, input: ActivateInput) -> types.Provision:

    provision = models.Provision.objects.get(id=input.provision)
    controll_backend.activate_provision(provision)

    return provision


@strawberry.input
class DeActivateInput:
    provision: strawberry.ID


def deactivate(info: Info, input: DeActivateInput) -> types.Provision:

    provision = models.Provision.objects.get(id=input.provision)
    controll_backend.deactivate_provision(provision)

    return provision



@strawberry.input
class ReInitInput:
    agent: strawberry.ID | None = None


async def reinit(info: Info, input: ReInitInput) -> str:
    await persist_backend.on_reinit(agent_id=input.agent)

    return "ok"
