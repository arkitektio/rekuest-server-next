from kante.types import Info
import strawberry
from facade import types, models, inputs, unique
import hashlib
import json
import logging

logger = logging.getLogger(__name__)




def create_state_schema(
    info: Info, input: inputs.CreateStateSchemaInput
) -> types.StateSchema:

    schema = input.state_schema

    state_schema, _ = models.StateSchema.objects.update_or_create(
        hash=unique.hash_state_schema(schema),
        defaults=dict(
            name=schema.name,
            ports=[strawberry.asdict(i) for i in schema.ports],
            description="A state schema",
        ),
    )

    return state_schema



