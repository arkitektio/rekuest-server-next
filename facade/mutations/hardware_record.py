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


@strawberry.input
class CreateHardwareRecordInput:
    cpu_count: int | None = None
    cpu_frequency: float | None = None
    cpu_vendor_name: str | None = None
    instance_id: scalars.InstanceID | None = None


def create_hardware_record(info: Info, input: CreateHardwareRecordInput) -> types.HardwareRecord:

    registry, _ = models.Registry.objects.update_or_create(
        app=info.context.request.app,
        user=info.context.request.user,
    )

    agent, _ = models.Agent.objects.update_or_create(
        registry=registry,
        instance_id=input.instance_id or "default",
        defaults=dict(
            name=f"{str(registry)} on {input.instance_id}",
        ),
    )

   
    record = models.HardwareRecord.objects.create(
        cpu_count=input.cpu_count,
        cpu_frequency=input.cpu_frequency,
        cpu_vendor_name=input.cpu_vendor_name or "Unknown",
        agent=agent

    )

    return record

