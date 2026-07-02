from enum import Enum

import strawberry
from django.db.models import TextChoices


class AgentEventChoices(TextChoices):
    DISCONNECT = "DISCONNECT", "Disconnect (Agent disconnected)"
    CONNECT = "CONNECT", "Connect (Agent connected)"


@strawberry.enum(description="The event kind of the agentevent")
class AgentEventKind(str, Enum):
    DISCONNECT = "DISCONNECT"
    CONNECT = "CONNECT"


@strawberry.enum
class AgentStatus(str, Enum):
    ACTIVE = "ACTIVE"
    KICKED = "KICKED"
    DISCONNECTED = "DISCONNECTED"
    VANILLA = "VANILLA"


@strawberry.enum
class AgentKind(str, Enum):
    WEBSOCKET = "WEBSOCKET"
    WEBHOOK = "WEBHOOK"
