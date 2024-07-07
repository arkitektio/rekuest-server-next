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
class AgentInput:
    instance_id: scalars.InstanceID 
    name: str | None = None
    extensions: list[str] | None = None



async def ensure_agent(info: Info, input: AgentInput) -> types.Agent:



    # TODO: Hasch this
    registry, _ = await models.Registry.objects.aupdate_or_create(
        app=info.context.request.app,
        user=info.context.request.user,
    )

    agent, _ = await models.Agent.objects.aupdate_or_create(
        registry=registry,
        instance_id=input.instance_id or "default",
        defaults=dict(
            name=input.name or f"{str(registry.id)} on {input.instance_id}",
            extensions=input.extensions,
        ),
    )


    return agent

