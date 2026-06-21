from enum import Enum

import strawberry
from django.db.models import TextChoices


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

    QUEUED = "QUEUED", "Queued (Assignation was queued)"
    BOUND = "BOUND", "Bound (Assignation was bound to an Agent)"
    ASSIGN = "ASSIGN", "Assign (Agent accepted the Assignation)"
    UNASSIGN = "UNASSIGN", "Unassign (Agent received the Assignation)"
    PROGRESS = "PROGRESS", "Progress (Agent is making progress on the Assignation)"
    CANCELING = "CANCELING", "Unassign (Assignation was unassigned from an Agent)"
    CANCELLED = "CANCELLED", "Unassign (Assignation was unassigned from an Agent)"
    INTERUPTING = "INTERUPTING", "Interupting (Assignation was interupted)"
    INTERUPTED = "INTERUPTED", "Interupted (Assignation was interupted)"
    DELEGATE = "DELEGATE", "Delegate (Assignation was delegated to another Assignation)"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
    DISCONNECTED = "DISCONNECTED"

    YIELD = (
        "YIELD",
        "Yields (Agent yielded the result)",
    )  # One yield can be interpreted as a return
    DONE = "DONE", "Done (Agent finished the Assignation)"
    LOG = "LOG", "Log (Agent logged a message)"


class AssignationInstructChoices(TextChoices):
    """These are the possible events that are instructed to an Assignation."""

    ASSIGN = "ASSIGN", "Assign (Agent accepted the Assignation)"
    CANCEL = "CANCEL", "Unassign (Agent received the Assignation)"
    STEP = "STEP", "Step (Agent is making progress on the Assignation)"
    RESUME = "RESUME", "Resume (Agent resumed the Assignation)"
    PAUSE = "PAUSE", "Pause (Agent paused the Assignation)"
    INTERRUPT = "INTERRUPT", "Interrupt (Agent interupted the Assignation)"
    COLLECT = "COLLECT", "Collect instruction received"


@strawberry.enum(description="The event kind of the assignationevent")
class AssignationStatus(str, Enum):
    ASSIGNING = "ASSIGNING"
    ONGOING = "ONGOING"
    CRITICAL = "CRITICAL"
    CANCELLED = "CANCELLED"
    DONE = "DONE"


@strawberry.enum(description="The event kind of the assignationevent")
class AssignationInstructKind(str, Enum):
    """These are the possible events that are instructed to an Assignation."""

    ASSIGN = "ASSIGN"
    CANCEL = "CANCEL"
    STEP = "STEP"
    RESUME = "RESUME"
    PAUSE = "PAUSE"
    INTERRUPT = "INTERRUPT"
    COLLECT = "COLLECT"


@strawberry.enum(description="The event kind of the assignationevent")
class AssignationEventKind(str, Enum):
    """These are the possible events that can happen to an Assignation.

    The events are ordered by their appearance in the lifecycle of an Assignation.
    """

    BOUND = "BOUND"
    QUEUED = "QUEUED"
    ASSIGN = "ASSIGN"
    PROGRESS = "PROGRESS"
    DELEGATE = "DELEGATE"

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
