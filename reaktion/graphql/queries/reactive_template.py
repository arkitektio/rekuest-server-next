import hashlib
import json
import logging

import strawberry
import strawberry_django
from facade.protocol import infer_protocols
from facade.utils import hash_input
from kante.types import Info
from reaktion import enums, inputs, models, scalars, types


def reactive_template(info: Info, id: strawberry.ID) -> types.ReactiveTemplate:
    return models.ReactiveTemplate.objects.get(id=id)
