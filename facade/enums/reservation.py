from enum import Enum

import strawberry
from django.db.models import TextChoices


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


@strawberry.enum(description="The pattern of assignment of the reservation")
class ReservationStrategy(str, Enum):
    RANDOM = "RANDOM"
    ROUND_ROBIN = "ROUND_ROBIN"
    LEAST_BUSY = "LEAST_BUSY"
    LEAST_TIME = "LEAST_TIME"
    LEAST_LOAD = "LEAST_LOAD"
    DIRECT = "DIRECT"


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
