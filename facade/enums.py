from enum import Enum
import strawberry
from django.db.models import TextChoices


class NodeKindChoices(TextChoices):
    FUNCTION = "FUNCTION", "Function"
    GENERATOR = "GENERATOR", "Generator"


class LogLevelChoices(TextChoices):
    DEBUG = "DEBUG", "DEBUG Level"
    INFO = "INFO", "INFO Level"
    ERROR = "ERROR", "ERROR Level"
    WARN = "WARN", "WARN Level"


class AgentStatusChoices(TextChoices):
    ACTIVE = "ACTIVE", "Active"
    KICKED = "KICKED", "Just kicked"
    DISCONNECTED = "DISCONNECTED", "Disconnected"
    VANILLA = "VANILLA", "Complete Vanilla Scenario after a forced restart of"


class WaiterStatusChoices(TextChoices):
    ACTIVE = "ACTIVE", "Active"
    KICKED = "KICKED", "Just kicked"
    DISCONNECTED = "DISCONNECTED", "Disconnected"
    VANILLA = "VANILLA", "Complete Vanilla Scenario after a forced restart of"


class ReservationStatusChoices(TextChoices):
    # LifeCycle States
    ACTIVE = "ACTIVE", "ACTIVE (Reservation is active and accepts assignments"
    INACTIVE = (
        "INACTIVE",
        "INACTIVE (Reservation is connected but inactive and discards",
    )

    # Error States
    UNCONNECTED = (
        "UNCONNECTED",
        "UNCONNECTED (Reservation is lacking adequate connection to provision)",
    )

    # End States
    ENDED = "ENDED", "ENDED (Reservation is lacking and accepts assignments"


class ProvisionStatusChoices(TextChoices):
    # Start State
    DENIED = "DENIED", "Denied (Provision was rejected by the platform)"
    PENDING = (
        "PENDING",
        "Pending (Request has been created and waits for its initial creation)",
    )
    BOUND = (
        "BOUND",
        "Bound (Provision was bound to an Agent)",
    )
    PROVIDING = (
        "PROVIDING",
        "Providing (Request has been send to its Agent and waits for Result",
    )

    # Life States
    ACTIVE = "ACTIVE", "Active (Provision is currently active)"
    REFUSED = "REFUSED", "Denied (Provision was rejected by the App)"
    INACTIVE = "INACTIVE", "Inactive (Provision is currently not active)"
    CANCELING = "CANCELING", "Cancelling (Provisions is currently being cancelled)"
    DISCONNECTED = "LOST", "Lost (Subscribers to this Topic have lost their connection)"
    RECONNECTING = (
        "RECONNECTING",
        "Reconnecting (We are trying to Reconnect to this Topic)",
    )

    # End States
    ERROR = (
        "ERROR",
        "Error (Reservation was not able to be performed (See StatusMessage)",
    )
    CRITICAL = "CRITICAL", "Critical (Provision resulted in an critical system error)"
    ENDED = (
        "ENDED",
        "Ended (Provision was cancelled by the Platform and will no longer create Topics)",
    )
    CANCELLED = (
        "CANCELLED",
        "Cancelled (Provision was cancelled by the User and will no longer create Topics)",
    )


class AssignationStatusChoices(TextChoices):
    ASSIGNING = "ASSIGNING", "Assigning, (Assignation is being assigned to an Agent)"
    ONGOING = "ONGOING", "ONGOING (Assignation is currently being performed)"
    DONE = "DONE", "Done (Assignation finished the Assignation)"


class AssignationEventChoices(TextChoices):
    BOUND = "BOUND", "Bound (Assignation was bound to an Agent)"
    ASSIGN = "ASSIGN", "Assign (Agent accepted the Assignation)"
    UNASSIGN = "UNASSIGN", "Unassign (Agent received the Assignation)"
    PROGRESS = "PROGRESS", "Progress (Agent is making progress on the Assignation)"

    YIELD = (
        "YIELD",
        "Yields (Agent yielded the result)",
    )  # One yield can be interpreted as a return
    DONE = "DONE", "Done (Agent finished the Assignation)"
    LOG = "LOG", "Log (Agent logged a message)"


class ReservationEventChoices(TextChoices):
    CHANGE = "CHANGE", "Change (Reservation changed its status)"
    LOG = "LOG", "Log (Reservation logged a message)"


class ProvisionEventChoices(TextChoices):
    CHANGE = "CHANGE", "Change (Provision changed its status)"
    LOG = "LOG", "Log (Provision logged a message)"


@strawberry.enum
class AssignationStatus(str, Enum):
    ASSIGNING = "ASSIGNING"
    ONGOING = "ONGOING"
    CRITICAL = "CRITICAL"
    CANCELLED = "CANCELLED"
    DONE = "DONE"


@strawberry.enum
class ReservationStatus(str, Enum):
    # LifeCycle States
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"

    # Error States
    UNCONNECTED = "UNCONNECTED"

    # End States
    ENDED = "ENDED"


@strawberry.enum
class ProvisionStatus(str, Enum):
    # Start State
    DENIED = "DENIED"
    PENDING = "PENDING"

    BOUND = "BOUND"
    PROVIDING = "PROVIDING"

    # Life States
    ACTIVE = "ACTIVE"
    REFUSED = "REFUSED"
    INACTIVE = "INACTIVE"
    CANCELING = "CANCELING"
    DISCONNECTED = "LOST"
    RECONNECTING = "RECONNECTING"

    # End States
    ERROR = ("ERROR",)
    CRITICAL = "CRITICAL"
    ENDED = "ENDED"
    CANCELLED = "CANCELLED"


@strawberry.enum
class AssignationEventKind(str, Enum):
    BOUND = "BOUND"
    ASSIGN = "ASSIGN"
    UNASSIGN = "UNASSIGN"
    PROGRESS = "PROGRESS"

    YIELD = "YIELD"
    DONE = "DONE"

    # Log Events
    LOG = "LOG"


@strawberry.enum
class ProvisionEventKind(str, Enum):
    CHANGE = "CHANGE"

    # Log Events
    LOG = "LOG"


@strawberry.enum
class ReservationEventKind(str, Enum):
    CHANGE = "CHANGE"

    # Log Events
    LOG = "LOG"


@strawberry.enum
class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    ERROR = "ERROR"
    WARN = "WARN"
    CRITICAL = "CRITICAL"


@strawberry.enum
class NodeKind(str, Enum):
    FUNCTION = "FUNCTION"
    GENERATOR = "GENERATOR"


@strawberry.enum
class AgentStatus(str, Enum):
    ACTIVE = "ACTIVE"
    KICKED = "KICKED"
    DISCONNECTED = "DISCONNECTED"
    VANILLA = "VANILLA"


@strawberry.enum
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


@strawberry.enum
class AssignWidgetKind(str, Enum):
    SEARCH = "SEARCH"
    CHOICE = "CHOICE"
    SLIDER = "SLIDER"
    CUSTOM = "CUSTOM"
    STRING = "STRING"


@strawberry.enum
class ReturnWidgetKind(str, Enum):
    CHOICE = "CHOICE"
    CUSTOM = "CUSTOM"


@strawberry.enum
class EffectKind(str, Enum):
    MESSAGE = "MESSAGE"
    CUSTOM = "CUSTOM"


@strawberry.enum
class LogicalCondition(str, Enum):
    IS = "IS"
    IS_NOT = "IS_NOT"
    IN = "IN"


@strawberry.enum
class PortScope(str, Enum):
    GLOBAL = "GLOBAL"
    LOCAL = "LOCAL"


@strawberry.enum
class NodeScope(str, Enum):
    GLOBAL = "GLOBAL"
    LOCAL = "LOCAL"
    BRIDGE_GLOBAL_TO_LOCAL = "BRIDGE_GLOBAL_TO_LOCAL"
    BRIDGE_LOCAL_TO_GLOBAL = "BRIDGE_LOCAL_TO_GLOBAL"
