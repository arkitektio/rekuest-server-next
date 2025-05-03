import strawberry
from enum import Enum


@strawberry.enum(description="The kind of action.")
class ActionKind(str, Enum):
    FUNCTION = "FUNCTION"
    GENERATOR = "GENERATOR"


@strawberry.enum(description="The kind of port.")
class PortKind(str, Enum):
    INT = "INT"
    STRING = "STRING"
    STRUCTURE = "STRUCTURE"
    LIST = "LIST"
    BOOL = "BOOL"
    DICT = "DICT"
    FLOAT = "FLOAT"
    DATE = "DATE"
    UNION = "UNION"
    MODEL = "MODEL"


@strawberry.enum(description="The kind of assign widget.")
class AssignWidgetKind(str, Enum):
    SEARCH = "SEARCH"
    CHOICE = "CHOICE"
    SLIDER = "SLIDER"
    CUSTOM = "CUSTOM"
    STRING = "STRING"
    STATE_CHOICE = "STATE_CHOICE"


@strawberry.enum(description="The kind of return widget.")
class ReturnWidgetKind(str, Enum):
    CHOICE = "CHOICE"
    CUSTOM = "CUSTOM"


@strawberry.enum(description="The kind of effect.")
class EffectKind(str, Enum):
    MESSAGE = "MESSAGE"
    HIDE = "HIDE"
    CUSTOM = "CUSTOM"


@strawberry.enum(description="The kind of port")
class PortScope(str, Enum):
    GLOBAL = "GLOBAL"
    LOCAL = "LOCAL"


@strawberry.enum(description="The kind of action scope.")
class ActionScope(str, Enum):
    GLOBAL = "GLOBAL"
    LOCAL = "LOCAL"
    BRIDGE_GLOBAL_TO_LOCAL = "BRIDGE_GLOBAL_TO_LOCAL"
    BRIDGE_LOCAL_TO_GLOBAL = "BRIDGE_LOCAL_TO_GLOBAL"
