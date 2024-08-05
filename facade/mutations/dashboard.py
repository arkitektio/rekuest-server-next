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


def create_dashboard(info: Info, input: inputs.CreateDashboardInput)-> types.Dashboard:

    return models.Dashboard.objects.create(
        tree = input.tree.dict()
    )

