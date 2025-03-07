from kante.types import Info
import strawberry_django
import strawberry
from facade import types, models, inputs, enums, scalars
import hashlib
import json
import logging
from facade.protocol import infer_protocols
from facade.utils import hash_input
import uuid

logger = logging.getLogger(__name__)


def create_toolbox(info: Info, input: inputs.CreateToolboxInput) -> types.Toolbox:

    toolbox, _ = models.Toolbox.objects.update_or_create(
        name=input.name,
        defaults=dict(description=input.description,
        creator=info.context.request.user,
        )
    )


    logger.info(f"Toolbox created: {toolbox}")

    return toolbox
