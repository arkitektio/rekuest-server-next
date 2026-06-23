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
    STARTED = "STARTED", "Started (Agent accepted and began the Assignation)"
    UNASSIGN = "UNASSIGN", "Unassign (Agent received the Assignation)"
    PROGRESS = "PROGRESS", "Progress (Agent is making progress on the Assignation)"
    CANCELLING = "CANCELLING", "Cancelling (a cancel was requested; awaiting the agent's confirmation)"
    CANCELLED = "CANCELLED", "Cancelled (the agent cancelled the assignation)"
    INTERRUPTING = "INTERRUPTING", "Interrupting (an interrupt was requested; awaiting the agent's confirmation)"
    INTERRUPTED = "INTERRUPTED", "Interrupted (the agent interrupted the assignation)"
    PAUSING = "PAUSING", "Pausing (a pause was requested; awaiting the agent's confirmation)"
    PAUSED = "PAUSED", "Paused (the agent suspended the assignation)"
    RESUMING = "RESUMING", "Resuming (a resume was requested; awaiting the agent's confirmation)"
    RESUMED = "RESUMED", "Resumed (the agent resumed the assignation)"
    DELEGATE = "DELEGATE", "Delegate (Assignation was delegated to another Assignation)"
    FAILED = "FAILED"
    CRITICAL = "CRITICAL"
    DISCONNECTED = "DISCONNECTED"

    YIELD = (
        "YIELD",
        "Yields (Agent yielded the result)",
    )  # One yield can be interpreted as a return
    COMPLETED = "COMPLETED", "Completed (Agent finished the Assignation)"
    LOG = "LOG", "Log (Agent logged a message)"


class AssignationInstructChoices(TextChoices):
    """These are the possible events that are instructed to an Assignation."""

    ASSIGN = "ASSIGN", "Assign (Agent accepted the Assignation)"
    CANCEL = "CANCEL", "Unassign (Agent received the Assignation)"
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
    STARTED = "STARTED"
    PROGRESS = "PROGRESS"
    DELEGATE = "DELEGATE"

    DISCONNECTED = "DISCONNECTED"

    YIELD = "YIELD"
    COMPLETED = "COMPLETED"

    # Log Events
    LOG = "LOG"
    CANCELLING = "CANCELLING"
    CANCELLED = "CANCELLED"
    INTERRUPTING = "INTERRUPTING"
    INTERRUPTED = "INTERRUPTED"
    PAUSING = "PAUSING"
    PAUSED = "PAUSED"
    RESUMING = "RESUMING"
    RESUMED = "RESUMED"
    FAILED = "FAILED"
    CRITICAL = "CRITICAL"
