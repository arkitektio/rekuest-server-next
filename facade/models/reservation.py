import uuid

from django.db import models
from django_choices_field import TextChoicesField

from facade import enums


class Reservation(models.Model):
    """Reservation (CONTRACT MODEL)

    Reflects RabbitMQ Channel

    Reservations are constant logs of active connections to Arkitekt and are logging the state of the connection to the workers. They are user facing
    and are created by the user, they hold a log of all transactions that have been done since its inception, as well as as of the inputs that it was
    created by (Action and Implementation as desired inputs) and the currently active Topics it connects to. It also specifies the routing policy (it case a
    connection to a worker/app gets lost). A Reservation creates also a (rabbitmq) Channel that every connected Topic listens to and the specific user assigns to.
    According to its Routing Policy, if a Topic dies another Topic can eithers take over and get the Items stored in this  (rabbitmq) Channel or a specific user  event
    happens with this Assignations.

    """

    causing_assignation = models.ForeignKey(
        "Assignation",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="caused_reservations",
        help_text="The assignation that created this reservation",
    )

    # Channel is the RabbitMQ channel that every user assigns to and that every topic listens to
    unique = models.UUIDField(
        max_length=1000,
        unique=True,
        default=uuid.uuid4,
        help_text="A Unique identifier for this Topic",
    )

    saved_args = models.JSONField(
        default=dict,
    )

    strategy = TextChoicesField(
        max_length=1000,
        choices_enum=enums.ReservationStrategyChoices,
        default=enums.ReservationStrategyChoices.RANDOM,
        help_text="The Strategy of this Reservation",
    )

    causing_dependency = models.ForeignKey(
        "Dependency",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="Was this Reservation caused by a Dependency?",
        related_name="caused_reservations",
    )

    registry = models.ForeignKey(
        "Registry",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="Which registry created this Reservation (if any?)",
        related_name="reservations",
    )

    # Meta fields of the creator of this
    allow_auto_request = models.BooleanField(
        default=False,
        help_text="Allow automatic requests for this reservation",
    )

    reference = models.CharField(
        max_length=200,
        help_text="A Short Hand Way to identify this reservation for the creating app",
        null=True,
        blank=True,
    )

    # 1 Inputs to the the Reservation (it can be either already a implementation to provision or just a action)
    action = models.ForeignKey(
        "Action",
        on_delete=models.CASCADE,
        help_text="The action this reservation connects",
        related_name="reservations",
    )
    title = models.CharField(
        max_length=200,
        help_text="A Short Hand Way to identify this reservation for you",
        null=True,
        blank=True,
    )

    # The connections
    implementations = models.ManyToManyField(
        "Implementation",
        help_text="The implementations this reservation connects",
        related_name="reservations",
    )

    # Platform specific Details (non relational Data)
    binds = models.JSONField(
        help_text="Params for the Policy (including Agent etc..)",
        null=True,
        blank=True,
    )

    statusmessage = models.CharField(
        max_length=1000,
        help_text="Clear Text status of the ssssssProvision as for now",
        blank=True,
    )

    # Meta fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
