import datetime
import uuid

from authentikate.models import Client, User
from django.db import models
from django_choices_field import TextChoicesField
from facade import enums
from django.contrib.auth import get_user_model

# Create your models here.


class Collection(models.Model):
    """A collection is a group of actions that are related to each other.

    You can put actions into a collection to group them together, and
    app developers can specify which collection a action belongs to
    by default.

    Collections should remain domain specific.

    Example collections are:
    - Segmentation
    - Classification
    - Image Processing


    """

    name = models.CharField(
        max_length=1000, unique=True, help_text="The name of this Collection"
    )
    description = models.TextField(help_text="A description for the Collection")
    defined_at = models.DateTimeField(
        auto_created=True,
        auto_now_add=True,
        help_text="Date this Collection was created",
    )
    updated_at = models.DateTimeField(
        auto_now=True, help_text="Date this Collection was last updated"
    )
    creator = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE,
        related_name="collections",
        help_text="The user that created this Collection",
    )


class Protocol(models.Model):
    """Protocols are ways to describe the input and output relations
    of a action. When a new action is created the
    interference module will try to infer the protocol of the action
    and assign it to the action. This is done by looking at the
    input and output types of the action and matching them to the
    protocols that are defined by your installed inference modules.

    """

    name = models.CharField(
        max_length=1000, unique=True, help_text="The name of this Protocol"
    )
    description = models.TextField(help_text="A description for the Protocol")

    def __str__(self) -> str:
        return self.name


class Registry(models.Model):
    """A registry is an app that is bound to a specific user on the
    backend.

    It is the root type for all agents and waiters that are
    created by this app.

    """

    client = models.ForeignKey(
        Client, on_delete=models.CASCADE, help_text="The Associated Client"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        help_text="The Associatsed User",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["client", "user"],
                name="No multiple Registries for same App and User allowed",
            )
        ]

    def __str__(self) -> str:
        return f"{self.client} used by {self.user}"


class IconPack(models.Model):
    """An IconPack is a collection of icons that are used to
    represent actions in the UI. You can create your own icon packs
    and use them to customize the look of your actions.

    """

    name = models.CharField(max_length=1000)


class Toolbox(models.Model):
    name = models.CharField(max_length=1000)
    description = models.TextField()
    creator = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE,
        related_name="toolboxes",
        help_text="The user that created this Shortcut",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Action(models.Model):
    """Actions are abstraction of RPC Tasks. They provide a common API to deal with creating tasks.

    See online Documentation"""

    collections = models.ManyToManyField(
        Collection,
        related_name="actions",
        help_text="The collections this Action belongs to",
    )
    pure = models.BooleanField(
        default=False, help_text="Is this function pure. e.g can we cache the result?"
    )
    idempotent = models.BooleanField(
        default=False,
        help_text="Is this function idempotent. e.g can we run it multiple times without changing the data again ?",
    )
    stateful = models.BooleanField(
        default=False,
        help_text="Is this function stateful. e.g does it inherently depend on or change state (think physical devices)?",
    )
    pinned_by = models.ManyToManyField(
        get_user_model(),
        related_name="pinned_actions",
        blank=True,
        help_text="The users that pinned this Actions",
    )
    kind = TextChoicesField(
        max_length=1000,
        choices_enum=enums.ActionKindChoices,
        default=enums.ActionKindChoices.FUNCTION.value,
        help_text="Function, generator? Will this function generate multiple results?",
    )
    interfaces = models.JSONField(
        default=list, help_text="Interfaces that we use to interpret the meta data"
    )
    port_groups = models.JSONField(
        default=list, help_text="Intercae that we use to interpret the meta data"
    )
    name = models.CharField(
        max_length=1000, help_text="The cleartext name of this Action"
    )
    description = models.TextField(help_text="A description for the Action")
    scope = models.CharField(
        max_length=1000,
        default="GLOBAL",
        help_text="The scope of this Action. e.g. does the data it needs or produce live only in the scope of this Action or is it global or does it bridge data?",
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
        related_name="actions",
        blank=True,
        help_text="The protocols this Action implements (e.g. Predicate)",
    )
    is_dev = models.BooleanField(
        default=False, help_text="Is this Action a development Action"
    )

    hash = models.CharField(
        max_length=1000,
        help_text="The hash of the Action (completely unique)",
        unique=True,
    )
    defined_at = models.DateTimeField(auto_created=True, auto_now_add=True)

    args = models.JSONField(default=list, help_text="Inputs for this Action")
    returns = models.JSONField(default=list, help_text="Outputs for this Action")

    def __str__(self):
        return f"{self.name}"


class Shortcut(models.Model):
    name: str = models.CharField(max_length=1000)
    description: str = models.TextField(null=True, blank=True)
    toolbox = models.ForeignKey(
        Toolbox, on_delete=models.CASCADE, related_name="shortcuts"
    )
    action = models.ForeignKey(
        Action, on_delete=models.CASCADE, related_name="shortcuts", null=True
    )
    implementation = models.ForeignKey(
        "Implementation", on_delete=models.CASCADE, related_name="shortcuts", null=True
    )
    saved_args = models.JSONField(default=dict)
    creator = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE,
        related_name="shortcuts",
        help_text="The user that created this Shortcut",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    args = models.JSONField(default=list, help_text="Inputs for this Shortcut")
    returns = models.JSONField(default=list, help_text="Outputs for this Shortcut")
    allow_quick = models.BooleanField(
        default=False,
        help_text="Allow quick execution of this Shortcut (e.g. run without confirmation)",
    )
    use_returns = models.BooleanField(
        default=False,
        help_text="Use the result of this Shortcut (e.g. use the result in the next Shortcut)",
    )


class Icon(models.Model):
    pack = models.ForeignKey(IconPack, on_delete=models.CASCADE)
    icon_url = models.CharField(max_length=10000)
    hash = models.CharField(max_length=1000)
    action = models.ForeignKey(
        Action, on_delete=models.SET_NULL, null=True, related_name="icons"
    )


class Agent(models.Model):
    name = models.CharField(
        max_length=2000, help_text="This providers Name", default="Nana"
    )
    extensions = models.JSONField(
        max_length=2000,
        default=list,
        help_text="The extensions for this Agent",
    )

    health_check_interval = models.IntegerField(
        default=60 * 5,
        help_text="How often should this agent be checked for its health. Defaults to 5 mins",
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
    latest_event = TextChoicesField(
        max_length=1000,
        choices_enum=enums.AgentEventChoices,
        default=enums.AgentEventChoices.DISCONNECT,
        help_text="The Status of this Agent",
    )
    connected = models.BooleanField(
        default=False, help_text="Is this Agent connected to the backend"
    )
    last_seen = models.DateTimeField(
        help_text="The last time this Agent was seen", null=True
    )
    pinned_by = models.ManyToManyField(
        get_user_model(),
        related_name="pinned_agents",
        blank=True,
        help_text="The users that pinned this Agent",
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
        return f"{self.name}"

    @property
    def queue(self):
        return f"agent_{self.unique}"

    @property
    def is_active(self):
        return (
            self.connected
            and self.last_seen > datetime.datetime.now() - datetime.timedelta(minutes=5)
        )


class FilesystemShelve(models.Model):
    """A shelve is a collection of shelved items that are
    related to each other. Shelves are used to group shelved
    items together and provide a way to access them.

    Shelves are not directly accessible by the user, but are
    used by the agent to store and manage shelved items.

    """

    name = models.CharField(max_length=1000)
    description = models.TextField()
    creator = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE,
        related_name="filesystem_shelves",
        help_text="The user that created this Shelf",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resource_id = models.CharField(
        max_length=1000,
        default=uuid.uuid4,
        help_text="The Channel we are listening to",
    )
    agents = models.ManyToManyField(
        "Agent",
        help_text="The associated agent for this shelved item",
        related_name="filesystem_shelves",
    )


class FileDrawer(models.Model):
    """A shelve is a collection of shelved items that are
    related to each other. Shelves are used to group shelved
    items together and provide a way to access them.

    Shelves are not directly accessible by the user, but are
    used by the agent to store and manage shelved items.

    """

    shelve = models.ForeignKey(
        FilesystemShelve,
        on_delete=models.CASCADE,
        help_text="The associated shelve for this drawer",
        related_name="drawers",
    )
    resource_id = models.CharField(
        max_length=1000,
        help_text="The resource id of this drawer",
        null=True,
        blank=True,
    )
    identifier = models.CharField(
        max_length=1000,
        help_text="The identifier of this drawer",
    )
    label = models.CharField(max_length=1000, null=True)
    description = models.TextField(null=True)


class MemoryShelve(models.Model):
    """A shelve is a collection of shelved items that are
    related to each other. Shelves are used to group shelved
    items together and provide a way to access them.

    Shelves are not directly accessible by the user, but are
    used by the agent to store and manage shelved items.

    """

    agent = models.OneToOneField(
        Agent,
        on_delete=models.CASCADE,
        help_text="The associated agent for this memory shelve",
        related_name="memory_shelve",
    )

    name = models.CharField(max_length=1000)
    description = models.TextField()
    creator = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE,
        related_name="shelves",
        help_text="The user that created this Shelf",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class MemoryDrawer(models.Model):
    """A shelve is a collection of shelved items that are
    related to each other. Shelves are used to group shelved
    items together and provide a way to access them.

    Shelves are not directly accessible by the user, but are
    used by the agent to store and manage shelved items.

    """

    shelve = models.ForeignKey(
        MemoryShelve,
        on_delete=models.CASCADE,
        help_text="The associated shelve for this drawer",
        related_name="drawers",
    )
    resource_id = models.CharField(
        max_length=1000,
        help_text="The resource id of this drawer",
        null=True,
        blank=True,
    )
    identifier = models.CharField(
        max_length=1000,
        help_text="The identifier of this drawer",
    )
    label = models.CharField(max_length=1000, null=True)
    description = models.TextField(null=True)


class HardwareRecord(models.Model):
    agent = models.ForeignKey(
        Agent,
        on_delete=models.CASCADE,
        help_text="The associated agent for this HardwareRecord",
        related_name="hardware_records",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    cpu_count = models.IntegerField(default=0)
    cpu_vendor_name = models.CharField(max_length=1000, default="Unknown")
    cpu_frequency = models.FloatField(default=0)


class Waiter(models.Model):
    name = models.CharField(
        max_length=2000, help_text="This waiters Name", default="Nana"
    )
    instance_id = models.CharField(default="main", max_length=1000)
    installed_at = models.DateTimeField(auto_created=True, auto_now_add=True)
    unique = models.CharField(
        max_length=1000, default=uuid.uuid4, help_text="The Channel we are listening to"
    )
    latest_event = TextChoicesField(
        max_length=1000,
        choices_enum=enums.WaiterStatusChoices,
        default=enums.WaiterStatusChoices.VANILLA,
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
    """A Dependency

    Dependencies are predeclared dependencies for functions
    that will only ever rely on a specific set of functionality

    Functions that declare dependencies CANNOT dynamically
    reserve new functionality.


    """

    implementation = models.ForeignKey(
        "Implementation",
        on_delete=models.CASCADE,
        help_text="The Implementation that has this dependency",
        related_name="dependencies",
    )
    action = models.ForeignKey(
        Action,
        on_delete=models.CASCADE,
        help_text="The action this dependency is for",
        related_name="dependees",
        null=True,
        blank=True,
    )
    initial_hash = models.CharField(
        max_length=1000,
        help_text="The initial hash of the Action",
        null=True,
        blank=True,
    )
    reference = models.CharField(
        max_length=2000,
        help_text="A reference for this dependency",
        null=True,
        blank=True,
    )
    optional = models.BooleanField(
        default=False,
        help_text="Is this dependency optional (e.g. can we still use the implementation if this dependency is not met)",
    )
    binds = models.JSONField(
        default=dict,
        help_text="The binds for this dependency (Determines which implementations can be used for this dependency)",
        null=True,
        blank=True,
    )


class Implementation(models.Model):
    """A Implementation is a conceptual implementation of A Action. It represents its implementation as well as its performance"""

    interface = models.CharField(
        max_length=1000, help_text="Interface (think Function)"
    )
    action = models.ForeignKey(
        Action,
        on_delete=models.CASCADE,
        help_text="The action this implementation is implementatig",
        related_name="implementations",
    )
    agent = models.ForeignKey(
        Agent,
        on_delete=models.CASCADE,
        help_text="The associated registry for this Implementation",
        related_name="implementations",
    )
    name = models.CharField(
        max_length=1000,
        default="Unnamed",
        help_text="A name for this Implementation",
    )
    pinned_by = models.ManyToManyField(
        get_user_model(),
        related_name="pinned_implementations",
        blank=True,
        help_text="The users that pinned this Agent",
    )
    extensions = models.JSONField(
        max_length=2000,
        default=list,
        help_text="The attached extensions for this Implementation",
    )
    extension = models.CharField(
        verbose_name="Extension", max_length=1000, default="global"
    )

    policy = models.JSONField(
        max_length=2000,
        default=dict,
        help_text="The attached policy for this implementation",
    )
    params = models.JSONField(default=dict, help_text="Params for this Implementation")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    dynamic: str = models.BooleanField(
        help_text="Dynamic Implementations will be able to create new reservations on runtime"
    )

    class Meta:
        permissions = [("providable", "Can provide this implementation")]
        constraints = [
            models.UniqueConstraint(
                fields=["interface", "agent"],
                name="A implementation has unique versions for every action it trys to implement",
            )
        ]

    def __str__(self):
        return f"{self.action} implemented by {self.agent}"


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

    waiter = models.ForeignKey(
        Waiter,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        max_length=1000,
        help_text="Which Waiter created this Reservation (if any?)",
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
        Action,
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
        Implementation,
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


class Assignation(models.Model):
    """A constant log of a tasks transition through finding a Action, Implementation and finally Pod , also a store for its results"""

    waiter = models.ForeignKey(
        Waiter, on_delete=models.CASCADE, help_text="Which Waiter assigned this?"
    )
    reservation = models.ForeignKey(
        Reservation,
        on_delete=models.CASCADE,
        help_text="Was this assigned through a reservation?",
        related_name="assignations",
        blank=True,
        null=True,
    )
    implementation = models.ForeignKey(
        Implementation,
        on_delete=models.CASCADE,
        help_text="Which implementation is the assignation currently mapped (can be reassigned)?",
        related_name="assignations",
        blank=True,
        null=True,
    )
    action = models.ForeignKey(
        Action, on_delete=models.CASCADE, help_text="The action this was assigned to"
    )
    ephemeral = models.BooleanField(
        default=False,
        help_text="Is this Assignation ephemeral (e.g. should it be deleted after its done or should it be kept for future reference)",
    )
    hooks = models.JSONField(
        default=list,
        help_text="hooks that are tight to the lifecycle of this assignation",
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
        help_text="The Assignations parent (the one that created this (none if there is no parent))",
        related_name="children",
    )
    root = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="The Root parent (the one that was created by the user (none if this is the root))",
        related_name="all_children",
    )
    args = models.JSONField(blank=True, null=True, help_text="The Args", default=dict)
    waiter = models.ForeignKey(
        Waiter,
        on_delete=models.CASCADE,
        max_length=1000,
        help_text="This Assignation app",
        null=True,
        blank=True,
        related_name="assignations",
    )
    agent = models.ForeignKey(
        Agent,
        on_delete=models.CASCADE,
        max_length=1000,
        help_text="This Assignation app",
        related_name="assignations",
    )
    latest_event_kind = TextChoicesField(
        max_length=1000,
        choices_enum=enums.AssignationEventChoices,
        help_text="The latest Status of this Provision (transitioned by events)",
    )
    latest_instruct_kind = TextChoicesField(
        max_length=1000,
        choices_enum=enums.AssignationInstructChoices,
        help_text="The latest Instruct of this Provision (transitioned by events)",
    )
    statusmessage = models.CharField(
        max_length=1000,
        help_text="Clear Text status of the Provision as for now",
        blank=True,
    )
    is_done = models.BooleanField(
        default=False,
        help_text="Is this Assignation done (e.g. has it been completed and resulted in an error?)",
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
        help_text="The returns of the events (true for yield events)",
        null=True,
        blank=True,
    )
    progress = models.IntegerField(
        help_text="The progress of the assignation (0-100) (set for yield events)",
        null=True,
        blank=True,
    )
    message = models.CharField(max_length=30000, null=True, blank=True)
    # Status Field
    kind = TextChoicesField(
        max_length=1000,
        choices_enum=enums.AssignationEventChoices,
        help_text="The event kind",
    )
    level = TextChoicesField(
        max_length=1000,
        choices_enum=enums.AssignationEventChoices,
        help_text="The log level",
        null=True,
        blank=True,
    )


class AssignationInstruct(models.Model):
    waiter = models.ForeignKey(
        Waiter,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        max_length=1000,
        help_text="Which Waiter created this Instruction (if any?)",
        related_name="instructions",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    assignation = models.ForeignKey(
        Assignation,
        help_text="The reservation this log item belongs to",
        related_name="instructs",
        on_delete=models.CASCADE,
    )
    # Status Field
    kind = TextChoicesField(
        max_length=1000,
        choices_enum=enums.AssignationInstructChoices,
        help_text="The event kind",
    )


class AgentEvent(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    agent = models.ForeignKey(
        Agent,
        help_text="The agent",
        related_name="events",
        on_delete=models.CASCADE,
    )
    message = models.CharField(max_length=2000, null=True, blank=True)
    # Status Field
    kind = TextChoicesField(
        max_length=1000,
        choices_enum=enums.AgentEventChoices,
        help_text="The event kind",
    )
    level = TextChoicesField(
        max_length=1000,
        choices_enum=enums.LogLevelChoices,
        help_text="The event level",
        null=True,
        blank=True,
    )


class TestCase(models.Model):
    action = models.ForeignKey(
        Action,
        on_delete=models.CASCADE,
        related_name="test_cases",
        help_text="The action this test belongs to",
    )
    tester = models.ForeignKey(
        Action,
        on_delete=models.CASCADE,
        related_name="testing_cases",
        help_text="The action that is testing this test",
    )
    name = models.CharField(max_length=2000, null=True, blank=True)
    description = models.CharField(max_length=2000, null=True, blank=True)
    is_benchmark = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["action", "tester"],
                name="No multiple Tests for same Action and Tester allowed",
            )
        ]


class TestResult(models.Model):
    case = models.ForeignKey(TestCase, on_delete=models.CASCADE, related_name="results")
    implementation = models.ForeignKey(
        Implementation, on_delete=models.CASCADE, related_name="testresults"
    )
    tester = models.ForeignKey(
        Implementation,
        on_delete=models.CASCADE,
        related_name="testing_results",
        help_text="The implementation that is testing this test",
    )
    passed = models.BooleanField(default=False)
    result = models.JSONField(default=dict, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class Structure(models.Model):
    identifier = models.CharField(max_length=2000, unique=True)
    label = models.CharField(max_length=2000)
    description = models.CharField(max_length=2000)


class Widget(models.Model):
    structure = models.ForeignKey(
        Structure, on_delete=models.CASCADE, null=True, blank=True
    )
    name = models.CharField(max_length=2000)
    kind = models.CharField(max_length=2000)
    hash = models.CharField(max_length=2000, unique=True)
    values = models.JSONField(null=True, blank=True)


class Dashboard(models.Model):
    name = models.CharField(max_length=2000)
    structure = models.ForeignKey(
        Structure, on_delete=models.CASCADE, null=True, blank=True
    )
    ui_tree = models.JSONField(null=True, blank=True)
    panels = models.ManyToManyField("Panel", related_name="dashboard")


class Panel(models.Model):
    name = models.CharField(max_length=2000, default="Unnamed")
    kind = models.CharField(max_length=2000)
    state = models.ForeignKey(
        "State", on_delete=models.CASCADE, related_name="panels", null=True, blank=True
    )
    reservation = models.ForeignKey(
        Reservation,
        on_delete=models.CASCADE,
        related_name="panels",
        null=True,
        blank=True,
    )
    implementation = models.ForeignKey(
        Implementation,
        on_delete=models.CASCADE,
        related_name="panels",
        null=True,
        blank=True,
    )
    accessors = models.JSONField(null=True, blank=True)
    submit_on_change = models.BooleanField(default=False)
    submit_on_load = models.BooleanField(default=False)


class StateSchema(models.Model):
    """A state schema is an abstract representation of a state and describes
    the ports (datatypes) that a state can have. States also follow the
    port schema

    State schemas do not belong directly to an agent, but are
    used by agents to describe the states they can have.

    The concept is closing linked to the concepot of a "Action", but
    representing state, rather than a function.


    """

    name = models.CharField(max_length=2000)
    hash = models.CharField(max_length=2000, unique=True)
    ports = models.JSONField(default=dict)
    description = models.CharField(max_length=2000)


class State(models.Model):
    """A state is a representation of the current state of a action.

    States always follow a schema and represent the current
    state of a action. States are used to represent the current

    """

    state_schema = models.ForeignKey(
        StateSchema, on_delete=models.CASCADE, related_name="states"
    )
    interface = models.CharField(
        max_length=1000,
        help_text="The interface this state is for (e.g. Function)",
    )
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name="states")
    value = models.JSONField(default=dict, help_text=" The current value of this state")
    created_at = models.DateTimeField(
        auto_now_add=True, help_text="Date this State was first ever written to"
    )
    updated_at = models.DateTimeField(
        auto_now=True, help_text="Date this State was last updated"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["interface", "agent"],
                name="No multiple States for same Agent and Schema allowed",
            )
        ]


class HistoricalState(models.Model):
    """A historical state

    A historical state is a frzoen state of an agent at a specific
    point in time. Historical states are used to conserve the
    state of an agent at a specific point in time, for example
    for debugging or for testing purposes.


    """

    state = models.ForeignKey(
        State, on_delete=models.CASCADE, related_name="historical_states"
    )
    value = models.JSONField(
        default=dict, help_text=" The  value of this state atht he time of creation"
    )
    archived_at = models.DateTimeField(
        auto_now_add=True, help_text="Date this State was archived"
    )



import facade.signals as signals # noqa: E402

__all__ = ["signals"]