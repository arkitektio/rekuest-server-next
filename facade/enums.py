from enum import Enum

import strawberry
from django.db.models import TextChoices


class NodeKindChoices(TextChoices):
    FUNCTION = "FUNCTION", "Function"
    GENERATOR = "GENERATOR", "Generator"


class PanelKindChoices(TextChoices):
    STATE = "STATE", "State"
    ASSIGN = "ASSIGN", "Assign"
    TEMPLATE = "TEMPLATE", "Template"

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
    # unhappy path
    UNHAPPY = "UNHAPPY"
    HAPPY = "HAPPY"


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
    BOUND = "BOUND", "Bound (Assignation was bound to an Agent)"
    CANCELING = "CANCELING", "Unassign (Assignation was unassigned from an Agent)"
    CANCELLED = "CANCELLED", "Unassign (Assignation was unassigned from an Agent)"
    ONGOING = "ONGOING", "ONGOING (Assignation is currently being performed)"
    DONE = "DONE", "Done (Assignation finished the Assignation)"
    ERROR = "ERROR", "Error (Assignation resulted in an error)"


class AssignationEventChoices(TextChoices):
    """These are the possible events that can happen to an Assignation.

    The events are ordered by their appearance in the lifecycle of an Assignation.


    """

    QUEUED = "QUEUED", "Queued (Assignation was queued for a reservation)"
    BOUND = "BOUND", "Bound (Assignation was bound to an Agent)"
    ASSIGN = "ASSIGN", "Assign (Agent accepted the Assignation)"
    UNASSIGN = "UNASSIGN", "Unassign (Agent received the Assignation)"
    PROGRESS = "PROGRESS", "Progress (Agent is making progress on the Assignation)"
    CANCELING = "CANCELING", "Unassign (Assignation was unassigned from an Agent)"
    CANCELLED = "CANCELLED", "Unassign (Assignation was unassigned from an Agent)"
    INTERUPTING = "INTERUPTING", "Interupting (Assignation was interupted)"
    INTERUPTED = "INTERUPTED", "Interupted (Assignation was interupted)"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
    DISCONNECTED = "DISCONNECTED"

    YIELD = (
        "YIELD",
        "Yields (Agent yielded the result)",
    )  # One yield can be interpreted as a return
    DONE = "DONE", "Done (Agent finished the Assignation)"
    LOG = "LOG", "Log (Agent logged a message)"


class ReservationEventChoices(TextChoices):
    PENDING = "PENDING", "Pending (Reservation is pending)"
    CREATE = "CREATE"
    RESCHEDULE = "RESCHEDULE"
    DELETED = "DELETED"
    CHANGE = "CHANGE"
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    # Error States
    UNCONNECTED = "UNCONNECTED"

    # End States
    ENDED = "ENDED"
    # unhappy path
    UNHAPPY = "UNHAPPY"
    HAPPY = "HAPPY"
    # Log Events
    LOG = "LOG"


class ProvisionEventChoices(TextChoices):
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
    LOG = "LOG", "Log (Provision logged a message)"

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
    UNHAPPY = "UNHAPPY"

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


class ReservationStrategyChoices(TextChoices):
    RANDOM = "RANDOM", "Random (Assignation is assigned to a random Provision)"
    ROUND_ROBIN = (
        "ROUND_ROBIN",
        "Round Robin (Assignation is assigned to the next Provision)",
    )
    LEAST_BUSY = (
        "LEAST_BUSY",
        "Least Busy (Assignation is assigned to the least busy Provision)",
    )
    LEAST_TIME = (
        "LEAST_TIME",
        "Least Time (Assignation is assigned to the Provision with the least time left)",
    )
    LEAST_LOAD = (
        "LEAST_LOAD",
        "Least Load (Assignation is assigned to the Provision with the least load)",
    )
    DIRECT = "DIRECT", "Direct (Assignation is assigned to a direct Provision)"


@strawberry.enum
class ReservationStrategy(str, Enum):
    RANDOM = "RANDOM"
    ROUND_ROBIN = "ROUND_ROBIN"
    LEAST_BUSY = "LEAST_BUSY"
    LEAST_TIME = "LEAST_TIME"
    LEAST_LOAD = "LEAST_LOAD"
    DIRECT = "DIRECT"


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

    # unhappy path
    UNHAPPY = "UNHAPPY"
    HAPPY = "HAPPY"

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
    """ These are the possible events that can happen to an Assignation.
    
    The events are ordered by their appearance in the lifecycle of an Assignation.
    """

    BOUND = "BOUND"
    ASSIGN = "ASSIGN"
    PROGRESS = "PROGRESS"

    DISCONNECTED = "DISCONNECTED"

    YIELD = "YIELD"
    DONE = "DONE"

    # Log Events
    LOG = "LOG"
    CANCELING = "CANCELING"
    CANCELLED = "CANCELLED"
    INTERUPTING = "INTERUPTING"
    INTERUPTED = ("INTERUPTED",)
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@strawberry.enum
class ProvisionEventKind(str, Enum):
    CHANGE = "CHANGE"
    UNHAPPY = "UNHAPPY"
    PENDING = "PENDING"
    CRITICAL = "CRITICAL"
    # Start State
    DENIED = "DENIED"

    # Life States
    ACTIVE = "ACTIVE"
    REFUSED = "REFUSED"
    INACTIVE = "INACTIVE"
    CANCELING = "CANCELING"
    DISCONNECTED = "LOST"
    RECONNECTING = "RECONNECTING"

    # End States
    ERROR = ("ERROR",)
    ENDED = "ENDED"
    CANCELLED = "CANCELLED"

    BOUND = "BOUND"
    PROVIDING = "PROVIDING"
    LOG = "LOG"


@strawberry.enum
class ReservationEventKind(str, Enum):
    PENDING = "PENDING"
    CREATE = "CREATE"
    RESCHEDULE = "RESCHEDULE"
    DELETED = "DELETED"
    CHANGE = "CHANGE"
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    # Error States
    UNCONNECTED = "UNCONNECTED"

    # End States
    ENDED = "ENDED"
    # unhappy path
    UNHAPPY = "UNHAPPY"
    HAPPY = "HAPPY"
    # Log Events
    LOG = "LOG"


class LogLevelChoices(TextChoices):
    DEBUG = "DEBUG", "DEBUG Level"
    INFO = "INFO", "INFO Level"
    ERROR = "ERROR", "ERROR Level"
    WARN = "WARN", "WARN Level"
    CRITICAL = "CRITICAL", "CRITICAL Level"


@strawberry.enum
class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    ERROR = "ERROR"
    WARN = "WARN"
    CRITICAL = "CRITICAL"


@strawberry.enum
class AgentStatus(str, Enum):
    ACTIVE = "ACTIVE"
    KICKED = "KICKED"
    DISCONNECTED = "DISCONNECTED"
    VANILLA = "VANILLA"


@strawberry.enum
class NodeScope(str, Enum):
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

@strawberry.enum
class JSONPatchOperation(str, Enum):
    add = "add"
    remove = "remove"
    replace = "replace"
    move = "move"
    copy = "copy"
    test = "test"


@strawberry.enum
class PanelKind(str, Enum):
    STATE = "STATE"
    ASSIGN = "ASSIGN"