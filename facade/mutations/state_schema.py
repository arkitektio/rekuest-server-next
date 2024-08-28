from kante.types import Info
import strawberry_django
import strawberry
from facade import types, models, inputs, enums, scalars
import hashlib
import json
import logging
from facade.protocol import infer_protocols
from facade.utils import hash_input

logger = logging.getLogger(__name__)

def underscore(s: str) -> str:
    return s.replace(" ", "_").replace("-", "_").lower()




def create_state_schema(info: Info, input: inputs.CreateStateSchemaInput)-> types.Dashboard:
   

    registry = models.Registry.objects.get(
        app=info.context.request.app,
        user=info.context.request.user,
    )

    agent = models.Agent.objects.get(
        registry=registry,
        instance_id=input.instance_id or "default",
    )

    schema = input.state_schema

    assert underscore(schema.name) == schema.name, "State schema names must be snake case lower letter"



    state_schema, _ = models.StateSchema.objects.update_or_create(
        agent = agent,
        name = underscore(schema.name),
        defaults = dict(
            ports = [strawberry.asdict(i) for i in schema.ports],
            description = "A state schema",
        )
    )

    return state_schema

