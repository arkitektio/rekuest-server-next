from kante.types import Info
import strawberry_django
import strawberry
from reaktion import types, models, inputs, enums, scalars
import hashlib
import json
import logging
from facade.protocol import infer_protocols
from facade.utils import hash_input
from reaktion.hashers import hash_graph
import namegenerator

logger = logging.getLogger(__name__)


@strawberry.input
class CreateTraceInput:
    flow: strawberry.ID
    provision: strawberry.ID
    snapshot_interval: int | None = None


def create_trace(info: Info, input: CreateTraceInput) -> types.Trace:
    trace, created = models.Trace.objects.update_or_create(
        flow_id=input.flow,
        provision_id=input.provision,
        defaults=dict(snapshot_interval=input.snapshot_interval),
    )

    return trace
