import datetime
from django.utils import timezone
import uuid

from authentikate.models import App, Device, Organization, Release, User
from django.contrib.auth import get_user_model
from django.db import models
from django_choices_field import TextChoicesField

from facade import enums


class Lock(models.Model):
    agent = models.ForeignKey(
        "Agent",
        on_delete=models.CASCADE,
        related_name="locks",
        help_text="The agent this lock belongs to",
    )
    key = models.CharField(max_length=2000, help_text="A unique identifier for this lock within the agent")
    description = models.TextField(help_text="A description for the Lock")
    created_at = models.DateTimeField(auto_created=True, auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    hold_by = models.ForeignKey(
        "Assignation",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="held_locks",
        help_text="The assigniation that currently holds this lock",
    )


class Agent(models.Model):
    app = models.ForeignKey(
        App,
        on_delete=models.CASCADE,
        related_name="agents",
        help_text="The app this agent belongs to (agents are part of an app and are NOT associated only with a release)",
    )
    hash = models.CharField(max_length=1000, help_text="The hash of the Agent (comparing the hash can be used to check if the agent has changed in a definition way)")
    release = models.ForeignKey(Release, on_delete=models.CASCADE, related_name="agents", help_text="The release this agent belongs to (agents are part of a release and are NOT associated only with an app)")
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name="agents", help_text="The device this agent belongs to (agents are part of a device and are NOT associated only with an app or release)")
    name = models.CharField(max_length=2000, help_text="This providers Name", default="Nana")
    extensions = models.JSONField(
        max_length=2000,
        default=list,
        help_text="The extensions for this Agent",
    )
    health_check_interval = models.IntegerField(
        default=60 * 5,
        help_text="How often should this agent be checked for its health. Defaults to 5 mins",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        help_text="The user this Agent belongs to",
    )
    instance_id = models.CharField(default="main", max_length=1000)
    installed_at = models.DateTimeField(auto_created=True, auto_now_add=True)
    unique = models.CharField(max_length=1000, default=uuid.uuid4, help_text="The Channel we are listening to")
    on_instance = models.CharField(
        max_length=1000,
        help_text="The Instance this Agent is running on",
        default="all",
    )
    kind = models.CharField(
        max_length=1000,
        choices=[(tag, tag.value) for tag in enums.AgentKind],
        default=enums.AgentKind.WEBSOCKET,
        help_text="The kind of this Agent",
    )
    hook_url = models.CharField(max_length=1000, help_text="The webhook URL for this Agent (only if webhook)", null=True, blank=True)
    hook_url_secret = models.CharField(max_length=1000, help_text="The webhook URL secret for this Agent (only if webhook)", null=True, blank=True)
    latest_event = TextChoicesField(
        max_length=1000,
        choices_enum=enums.AgentEventChoices,
        default=enums.AgentEventChoices.DISCONNECT,
        help_text="The Status of this Agent",
    )
    connected = models.BooleanField(default=False, help_text="Is this Agent connected to the backend")
    last_seen = models.DateTimeField(help_text="The last time this Agent was seen", null=True)
    pinned_by = models.ManyToManyField(
        get_user_model(),
        related_name="pinned_agents",
        blank=True,
        help_text="The users that pinned this Agent",
    )
    registry = models.ForeignKey(
        "Registry",
        on_delete=models.CASCADE,
        help_text="The provide might be limited to a instance like ImageJ belonging to a specific person. Is nullable for backend users",
        null=True,
        related_name="agents",
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        help_text="The organization this Agent belongs to",
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
        return self.connected and self.last_seen > timezone.now() - datetime.timedelta(minutes=5)


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
    name = models.CharField(max_length=2000, help_text="This waiters Name", default="Nana")
    instance_id = models.CharField(default="main", max_length=1000)
    installed_at = models.DateTimeField(auto_created=True, auto_now_add=True)
    unique = models.CharField(max_length=1000, default=uuid.uuid4, help_text="The Channel we are listening to")
    latest_event = TextChoicesField(
        max_length=1000,
        choices_enum=enums.WaiterStatusChoices,
        default=enums.WaiterStatusChoices.VANILLA,
        help_text="The Status of this Waiter",
    )
    registry = models.ForeignKey(
        "Registry",
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
