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


def hash_state_schema(definition: inputs.StateSchemaInput) -> str:
    hashable_schema = {
        key: value
        for key, value in dict(strawberry.asdict(definition)).items()
        if key in ["ports"]
    }
    return hashlib.sha256(
        json.dumps(hashable_schema, sort_keys=True).encode()
    ).hexdigest()


def create_state_schema(
    info: Info, input: inputs.CreateStateSchemaInput
) -> types.Dashboard:

    schema = input.state_schema

    state_schema, _ = models.StateSchema.objects.update_or_create(
        hash=hash_state_schema(schema),
        defaults=dict(
            name=underscore(schema.name),
            ports=[strawberry.asdict(i) for i in schema.ports],
            description="A state schema",
        ),
    )

    return state_schema
