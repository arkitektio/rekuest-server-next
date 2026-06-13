from enum import Enum

import strawberry
from django.db.models import TextChoices


class ActionKindChoices(TextChoices):
    FUNCTION = "FUNCTION", "Function"
    GENERATOR = "GENERATOR", "Generator"


@strawberry.enum
class ActionScope(str, Enum):
    GLOBAL = "GLOBAL"
    LOCAL = "LOCAL"
    BRIDGE_GLOBAL_TO_LOCAL = "BRIDGE_GLOBAL_TO_LOCAL"
    BRIDGE_LOCAL_TO_GLOBAL = "BRIDGE_LOCAL_TO_GLOBAL"


@strawberry.enum
class DemandKind(str, Enum):
    ARGS = "args"
    RETURNS = "returns"


@strawberry.enum
class HookKind(str, Enum):
    CLEANUP = "CLEANUP"
    INIT = "INIT"
