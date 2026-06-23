from enum import Enum

import strawberry
from django.db.models import TextChoices


class ActionKindChoices(TextChoices):
    FUNCTION = "FUNCTION", "Function"
    GENERATOR = "GENERATOR", "Generator"


class EffectClassChoices(TextChoices):
    """The effect class of an implementation (persisted on ``Implementation.effect``).

    NONE work is freely retryable/reclaimable; PHYSICAL work touches the real world, so an
    ambiguous failure is terminal and must not be retried. Read at runtime from
    ``task.implementation.effect`` — never supplied by the caller.
    """

    NONE = "NONE", "None (no real-world effect; freely retryable)"
    PHYSICAL = "PHYSICAL", "Physical (touches the real world; ambiguous failure is terminal)"


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
