from django.db import models
from django_choices_field import TextChoicesField
from facade.enums import (
    NodeKindChoices,
    AgentStatusChoices,
    WaiterStatusChoices,
    ProvisionStatusChoices,
    ReservationStatusChoices,
    AssignationEventChoices,
    AssignationStatusChoices,
    ProvisionEventChoices,
    ReservationEventChoices,
)
from authentikate.models import User, App
import uuid

# Create your models here.


class Collection(models.Model):
    name = models.CharField(
        max_length=1000, unique=True, help_text="The name of this Collection"
    )
    description = models.TextField(help_text="A description for the Collection")
    defined_at = models.DateTimeField(auto_created=True, auto_now_add=True)


class Protocol(models.Model):
    name = models.CharField(
        max_length=1000, unique=True, help_text="The name of this Protocol"
    )
    description = models.TextField(help_text="A description for the Protocol")

    def __str__(self) -> str:
        return self.name


class Registry(models.Model):
    app = models.ForeignKey(
        App, on_delete=models.CASCADE, null=True, help_text="The Associated App"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        help_text="The Associatsed User",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["app", "user"],
                name="No multiple Clients for same App and User allowed",
            )
        ]

    def __str__(self) -> str:
        return f"{self.app} used by {self.user}"


class Node(models.Model):
    """Nodes are abstraction of RPC Tasks. They provide a common API to deal with creating tasks.

    See online Documentation"""

    collections = models.ManyToManyField(
        Collection,
        related_name="nodes",
        help_text="The collections this Node belongs to",
    )
    pure = models.BooleanField(
        default=False, help_text="Is this function pure. e.g can we cache the result?"
    )
    idempotent = models.BooleanField(
        default=False, help_text="Is this function pure. e.g can we cache the result?"
    )
    kind = TextChoicesField(
        max_length=1000,
        choices_enum=NodeKindChoices,
        default=NodeKindChoices.FUNCTION.value,
        help_text="Function, generator? Check async Programming Textbook",
    )
    interfaces = models.JSONField(
        default=list, help_text="Intercae that we use to interpret the meta data"
    )
    port_groups = models.JSONField(
        default=list, help_text="Intercae that we use to interpret the meta data"
    )
    name = models.CharField(
        max_length=1000, help_text="The cleartext name of this Node"
    )
    meta = models.JSONField(
        null=True, blank=True, help_text="Meta data about this Node"
    )

    description = models.TextField(help_text="A description for the Node")
    scope = models.CharField(
        max_length=1000,
        default="GLOBAL",
        help_text="The scope of this Node. e.g. does the data it needs or produce live only in the scope of this Node or is it global or does it bridge data?",
    )
    is_test_for = models.ManyToManyField(
        "self",
        related_name="tests",
        blank=True,
        symmetrical=False,
        help_text="The users that have pinned the position",
    )
    protocols = models.ManyToManyField(
        Protocol,
        related_name="nodes",
        blank=True,
        help_text="The protocols this Node implements (e.g. Predicate)",
    )

    hash = models.CharField(
        max_length=1000,
        help_text="The hash of the Node (completely unique)",
        unique=True,
    )
    defined_at = models.DateTimeField(auto_created=True, auto_now_add=True)

    args = models.JSONField(default=list, help_text="Inputs for this Node")
    returns = models.JSONField(default=list, help_text="Outputs for this Node")

    def __str__(self):
        return f"{self.name}"


class Agent(models.Model):
    name = models.CharField(
        max_length=2000, help_text="This providers Name", default="Nana"
    )
    instance_id = models.CharField(default="main", max_length=1000)
    installed_at = models.DateTimeField(auto_created=True, auto_now_add=True)
    unique = models.CharField(
        max_length=1000, default=uuid.uuid4, help_text="The Channel we are listening to"
    )
    on_instance = models.CharField(
        max_length=1000,
        help_text="The Instance this Agent is running on",
        default="all",
    )
    status = TextChoicesField(
        max_length=1000,
        choices_enum=AgentStatusChoices,
        default=AgentStatusChoices.VANILLA,
        help_text="The Status of this Agent",
    )
    registry = models.ForeignKey(
        Registry,
        on_delete=models.CASCADE,
        help_text="The provide might be limited to a instance like ImageJ belonging to a specific person. Is nullable for backend users",
        null=True,
        related_name="agents",
    )
    blocked = models.BooleanField(
        default=False,
        help_text="If this Agent is blocked, it will not be used for provision, nor will it be able to provide",
    )

    class Meta:
        permissions = [("can_provide_on", "Can provide on this Agent")]
        constraints = [
            models.UniqueConstraint(
                fields=["registry", "instance_id"],
                name="No multiple Agents for same App and User allowed on same identifier",
            )
        ]

    def __str__(self):
        return f"{self.status} {self.registry} on {self.instance_id} managed by {self.on_instance}"

    @property
    def queue(self):
        return f"agent_{self.unique}"


class Waiter(models.Model):
    name = models.CharField(
        max_length=2000, help_text="This waiters Name", default="Nana"
    )
    instance_id = models.CharField(default="main", max_length=1000)
    installed_at = models.DateTimeField(auto_created=True, auto_now_add=True)
    unique = models.CharField(
        max_length=1000, default=uuid.uuid4, help_text="The Channel we are listening to"
    )
    status = TextChoicesField(
        max_length=1000,
        choices_enum=WaiterStatusChoices,
        default=WaiterStatusChoices.VANILLA,
        help_text="The Status of this Waiter",
    )
    registry = models.ForeignKey(
        Registry,
        on_delete=models.CASCADE,
        help_text="The provide might be limited to a instance like ImageJ belonging to a specific person. Is nullable for backend users",
        null=True,
        related_name="waiters",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["registry", "instance_id"],
                name="No multiple Waiters for same App and User allowed on same instance_id",
            )
        ]

    def __str__(self):
        return f"Waiter {self.registry} on {self.instance_id}"

    @property
    def queue(self):
        return f"waiter_{self.unique}"


class Dependency(models.Model):
    template = models.ForeignKey(
        "Template",
        on_delete=models.CASCADE,
        help_text="The Template that has this dependency",
        related_name="dependencies",
    )
    node = models.ForeignKey(
        Node,
        on_delete=models.CASCADE,
        help_text="The node this dependency is for",
        related_name="dependencies",
    )
    reference = models.CharField(
        max_length=1000,
        help_text="A reference for this dependency",
        null=True,
        blank=True,
    )
    optional = models.BooleanField(
        default=False,
        help_text="Is this dependency optional (e.g. can we still use the template if this dependency is not met)",
    )
    binds = models.JSONField(
        max_length=2000,
        default=dict,
        help_text="The binds for this dependency (Determines which templates can be used for this dependency)",
    )
    viable_instances = models.IntegerField(
        default=1,
        help_text="How many instances of this dependency do we need to be viable",
    )


class Template(models.Model):
    """A Template is a conceptual implementation of A Node. It represents its implementation as well as its performance"""

    interface = models.CharField(
        max_length=1000, help_text="Interface (think Function)"
    )
    node = models.ForeignKey(
        Node,
        on_delete=models.CASCADE,
        help_text="The node this template is implementatig",
        related_name="templates",
    )
    agent = models.ForeignKey(
        Agent,
        on_delete=models.CASCADE,
        help_text="The associated registry for this Template",
        related_name="templates",
    )
    name = models.CharField(
        max_length=1000,
        default="Unnamed",
        help_text="A name for this Template",
    )
    extensions = models.JSONField(
        max_length=2000,
        default=list,
        help_text="The attached extensions for this Template",
    )

    policy = models.JSONField(
        max_length=2000, default=dict, help_text="The attached policy for this template"
    )

    params = models.JSONField(default=dict, help_text="Params for this Template")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        permissions = [("providable", "Can provide this template")]
        constraints = [
            models.UniqueConstraint(
                fields=["interface", "agent"],
                name="A template has unique versions for every node it trys to implement",
            )
        ]

    def __str__(self):
        return f"{self.node} implemented by {self.agent} on {self.interface}"


class Provision(models.Model):
    """Topic (STATEFUL MODEL)

    Topic represents the current state of active Topics that are caused by provisions, they store the reservations (links)
    and are indexed by provision, a consumer connects through its provision to Arkitekt and sets the Topic to active, every
    reservation that is connected gets signalled that this Topic is now active. On disconnect every reservation can design
    according to its policy if it wants to wait for reconnect (if connection was Lost), raise an error, or choose another Topic.

    """

    agent = models.ForeignKey(
        Agent,
        on_delete=models.CASCADE,
        help_text="The associated agent for this Provision",
        related_name="provisions",
    )

    unique = models.UUIDField(
        max_length=1000,
        unique=True,
        default=uuid.uuid4,
        help_text="A Unique identifier for this Topic",
    )

    causing_reservation = models.ForeignKey(
        "Reservation",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="Reservation that created this provision",
        related_name="created_provisions",
    )

    # Provisions are bound to templates, and through that to an agent
    # A TEMPLATE CAN ONLY BE BOUND TO ONE PROVISION
    template = models.OneToOneField(
        Template,
        on_delete=models.CASCADE,
        help_text="The Template for this Provision",
        related_name="provision",
        null=True,
        blank=True,
    )

    # Status Field
    status = TextChoicesField(
        max_length=1000,
        choices_enum=ProvisionStatusChoices,
        default=ProvisionStatusChoices.INACTIVE,
        help_text="The Status of this Provision",
    )

    statusmessage = models.CharField(
        max_length=10000,
        help_text="Clear Text status of the Provision as for now",
        blank=True,
    )
    # Meta fields of the creator of this
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        permissions = [("can_link_to", "Can link a reservation to a provision")]

    @property
    def queue(self):
        return f"provision_{self.unique}"


class Reservation(models.Model):
    """Reservation (CONTRACT MODEL)

    Reflects RabbitMQ Channel

    Reservations are constant logs of active connections to Arkitekt and are logging the state of the connection to the workers. They are user facing
    and are created by the user, they hold a log of all transactions that have been done since its inception, as well as as of the inputs that it was
    created by (Node and Template as desired inputs) and the currently active Topics it connects to. It also specifies the routing policy (it case a
    connection to a worker/app gets lost). A Reservation creates also a (rabbitmq) Channel that every connected Topic listens to and the specific user assigns to.
    According to its Routing Policy, if a Topic dies another Topic can eithers take over and get the Items stored in this  (rabbitmq) Channel or a specific user  event
    happens with this Assignations.

    """

    # Channel is the RabbitMQ channel that every user assigns to and that every topic listens to
    unique = models.UUIDField(
        max_length=1000,
        unique=True,
        default=uuid.uuid4,
        help_text="A Unique identifier for this Topic",
    )

    causing_provision = models.ForeignKey(
        "Provision",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="Was this Reservation caused by a Provision?",
        related_name="caused_reservations",
    )

    waiter = models.ForeignKey(
        Waiter,
        on_delete=models.CASCADE,
        max_length=1000,
        help_text="This Reservations app",
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

    # 1 Inputs to the the Reservation (it can be either already a template to provision or just a node)
    node = models.ForeignKey(
        Node,
        on_delete=models.CASCADE,
        help_text="The node this reservation connects",
        related_name="reservations",
    )
    title = models.CharField(
        max_length=200,
        help_text="A Short Hand Way to identify this reservation for you",
        null=True,
        blank=True,
    )
    template = models.ForeignKey(
        Template,
        on_delete=models.CASCADE,
        help_text="The template this reservation connects",
        related_name="reservations",
        null=True,
        blank=True,
    )

    # The connections
    provisions = models.ManyToManyField(
        Provision,
        help_text="The Provisions this reservation connects",
        related_name="reservations",
        null=True,
        blank=True,
    )

    # Platform specific Details (non relational Data)
    binds = models.JSONField(
        help_text="Params for the Policy (including Agent etc..)",
        null=True,
        blank=True,
    )

    # Status Field
    status = TextChoicesField(
        max_length=1000,
        choices_enum=ReservationStatusChoices,
        default=ReservationStatusChoices.INACTIVE,
        help_text="The Status of this Provision",
    )
    statusmessage = models.CharField(
        max_length=1000,
        help_text="Clear Text status of the Provision as for now",
        blank=True,
    )

    # Meta fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Assignation(models.Model):
    """A constant log of a tasks transition through finding a Node, Template and finally Pod , also a store for its results"""

    reservation = models.ForeignKey(
        Reservation,
        on_delete=models.CASCADE,
        help_text="Which reservation are we assigning to",
        related_name="assignations",
        blank=True,
        null=True,
    )
    reference = models.CharField(
        max_length=1000,
        default=uuid.uuid4,
        help_text="The Unique identifier of this Assignation considering its parent",
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="The Assignations parent (the one that created this)",
        related_name="children",
    )

    args = models.JSONField(blank=True, null=True, help_text="The Args", default=list)
    provision = models.ForeignKey(
        Provision,
        on_delete=models.CASCADE,
        help_text="Which Provision did we end up being assigned to (will change after a bound)",
        related_name="assignations",
        blank=True,
        null=True,
    )
    waiter = models.ForeignKey(
        Waiter,
        on_delete=models.CASCADE,
        max_length=1000,
        help_text="This Assignation app",
        null=True,
        blank=True,
        related_name="assignations",
    )
    status = TextChoicesField(
        max_length=1000,
        choices_enum=AssignationEventChoices,
        help_text="The Status of this Provision (transitioned by events)",
    )
    statusmessage = models.CharField(
        max_length=1000,
        help_text="Clear Text status of the Provision as for now",
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.status} for {self.reservation}"

    class Meta:
        pass


class AssignationEvent(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    assignation = models.ForeignKey(
        Assignation,
        help_text="The reservation this log item belongs to",
        related_name="events",
        on_delete=models.CASCADE,
    )
    returns = models.JSONField(
        help_text="The return of the assignation",
        null=True,
        blank=True,
    )
    progress = models.IntegerField(
        help_text="The progress of the assignation",
    )
    message = models.CharField(max_length=2000, null=True, blank=True)
    # Status Field
    kind = TextChoicesField(
        max_length=1000,
        choices_enum=AssignationEventChoices,
        help_text="The event kind",
    )


class ReservationEvent(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    reservation = models.ForeignKey(
        Reservation,
        help_text="The reservation this log item belongs to",
        related_name="events",
        on_delete=models.CASCADE,
    )
    message = models.CharField(max_length=2000, null=True, blank=True)
    # Status Field
    kind = TextChoicesField(
        max_length=1000,
        choices_enum=ReservationEventChoices,
        help_text="The event kind",
    )


class ProvisionEvent(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    provision = models.ForeignKey(
        Provision,
        help_text="The provision this log item belongs to",
        related_name="events",
        on_delete=models.CASCADE,
    )
    message = models.CharField(max_length=2000, null=True, blank=True)
    # Status Field
    kind = TextChoicesField(
        max_length=1000,
        choices_enum=ProvisionEventChoices,
        help_text="The event kind",
    )


class TestCase(models.Model):
    node = models.ForeignKey(
        Node,
        on_delete=models.CASCADE,
        related_name="testcases",
        help_text="The node this test belongs to",
    )
    key = models.CharField(max_length=2000, null=True, blank=True)
    name = models.CharField(max_length=2000, null=True, blank=True)
    description = models.CharField(max_length=2000, null=True, blank=True)
    is_benchmark = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)


class TestResult(models.Model):
    case = models.ForeignKey(TestCase, on_delete=models.CASCADE, related_name="results")
    template = models.ForeignKey(
        Template, on_delete=models.CASCADE, related_name="testresults"
    )
    passed = models.BooleanField(default=False)
    result = models.JSONField(default=dict, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


import facade.signals
