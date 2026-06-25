from authentikate.models import App, Organization
from django.contrib.auth import get_user_model
from django.db import models
from django_choices_field import TextChoicesField

from facade import enums


class Action(models.Model):
    """Actions are abstraction of RPC Tasks. They provide a common API to deal with creating tasks.

    See online Documentation"""

    app = models.ForeignKey(
        App,
        on_delete=models.CASCADE,
        related_name="actions",
        help_text="The app this action belongs to (actions are part of an app and are NOT associated only with a release)",
    )
    key = models.CharField(max_length=2000, help_text="A unique identifier for this action within the app")
    version = models.CharField(max_length=100, help_text="The version of this action (e.g. 1.0.0), this is used to differentiate if the underyling algorithm has changed, i.e we would expect different results for the same input")
    collections = models.ManyToManyField(
        "Collection",
        related_name="actions",
        help_text="The collections this Action belongs to",
    )
    pure = models.BooleanField(default=False, help_text="Is this function pure. e.g can we cache the result?")
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
    logo = models.CharField(max_length=1000, blank=True, null=True, help_text="An optional icon identifier to represent this Action in the UI (e.g. 'fa-solid fa-dog')")
    interfaces = models.JSONField(default=list, help_text="Interfaces that we use to interpret the meta data")
    port_groups = models.JSONField(default=list, help_text="Intercae that we use to interpret the meta data")
    name = models.CharField(max_length=1000, help_text="The cleartext name of this Action (e.g. 'Segment Image')", default="Unnamed Action")
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
        "Protocol",
        related_name="actions",
        blank=True,
        help_text="The protocols this Action implements (e.g. Predicate)",
    )
    is_dev = models.BooleanField(default=False, help_text="Is this Action a development Action")

    hash = models.CharField(
        max_length=1000,
        help_text="The hash of the Action (completely unique)",
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="actions",
        help_text="The organization this Action belongs to",
    )
    defined_at = models.DateTimeField(auto_created=True, auto_now_add=True)

    args = models.JSONField(default=list, help_text="Inputs for this Action")
    returns = models.JSONField(default=list, help_text="Outputs for this Action")

    arg_count = models.IntegerField(default=0, help_text="Pre-calculated number of root input ports")
    return_count = models.IntegerField(default=0, help_text="Pre-calculated number of root output ports")

    def __str__(self) -> str:
        return f"{self.name}"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "app", "key", "version"],
                name="No multiple Actions with the same key and version in the same app for an organization allowed",
            )
        ]


class BasePort(models.Model):
    """
    Abstract base class containing all the shared schema for Args and Returns.
    This guarantees Django writes to two physically separate tables.
    """

    index = models.IntegerField(help_text="The position of this port in the list")
    key = models.CharField(max_length=255, null=True, help_text="The local key (e.g. 'mask')")

    # The Semantic Materialized Path for O(1) nested execution lookups
    key_path = models.CharField(max_length=500, db_index=True, help_text="The full dot-notation path (e.g. 'options.advanced.mask')")

    kind = models.CharField(max_length=50, null=True, help_text="The structural kind (e.g. LIST, DICT, INT)")
    identifier = models.CharField(max_length=255, null=True, db_index=True, help_text="The macro-type (e.g. '@mikro/image')")

    # The ECS JSONPath string compiler output
    compiled_jsonpath = models.CharField(max_length=1000, null=True, blank=True, help_text="PostgreSQL JSONPath string for micro-constraints")
    nullable = models.BooleanField(default=False)

    class Meta:
        abstract = True
        indexes = [
            # Composite index for instant payload resolution at execution time
            models.Index(fields=["action", "key_path"]),
            # Index for fast reverse-matching graph searches
            models.Index(fields=["identifier"]),
        ]


class ArgPort(BasePort):
    """Inputs for the Action"""

    action = models.ForeignKey(Action, on_delete=models.CASCADE, related_name="arg_ports")
    parent = models.ForeignKey("self", on_delete=models.CASCADE, null=True, blank=True, related_name="children", help_text="If this port is nested inside a LIST or DICT")

    def __str__(self):
        return f"Arg: {self.key_path} ({self.identifier})"


class ReturnPort(BasePort):
    """Outputs for the Action"""

    action = models.ForeignKey(Action, on_delete=models.CASCADE, related_name="return_ports")
    parent = models.ForeignKey("self", on_delete=models.CASCADE, null=True, blank=True, related_name="children", help_text="If this port is nested inside a LIST or DICT")

    def __str__(self):
        return f"Return: {self.key_path} ({self.identifier})"


class InputStructureUsage(models.Model):
    action = models.ForeignKey(
        Action,
        on_delete=models.CASCADE,
        related_name="input_structures_usages",
        help_text="The action this usage is for",
    )
    structure = models.ForeignKey(
        "Structure",
        on_delete=models.CASCADE,
        related_name="input_usages",
        help_text="The structure this usage is for",
    )
    port_index = models.IntegerField(help_text="The index of the port this structure is used for")
    port_key = models.CharField(max_length=2000, help_text="The key of the port this structure is used for")
    modifiers = models.JSONField(default=list)


class InputInterfaceUsage(models.Model):
    action = models.ForeignKey(
        Action,
        on_delete=models.CASCADE,
        related_name="input_interface_usages",
        help_text="The action this usage is for",
    )
    interface = models.ForeignKey(
        "Interface",
        on_delete=models.CASCADE,
        related_name="input_usages",
        help_text="The structure this usage is for",
    )
    port_index = models.IntegerField(help_text="The index of the port this structure is used for")
    port_key = models.CharField(max_length=2000, help_text="The key of the port this structure is used for")
    modifiers = models.JSONField(default=list)


class OutputStructureUsage(models.Model):
    action = models.ForeignKey(
        Action,
        on_delete=models.CASCADE,
        related_name="output_structure_usages",
        help_text="The action this usage is for",
    )
    structure = models.ForeignKey(
        "Structure",
        on_delete=models.CASCADE,
        related_name="output_usages",
        help_text="The structure this usage is for",
    )
    port_index = models.IntegerField(help_text="The index of the port this structure is used for")
    port_key = models.CharField(max_length=2000, help_text="The key of the port this structure is used for")
    modifiers = models.JSONField(default=list)


class OutputInterfaceUsage(models.Model):
    action = models.ForeignKey(
        Action,
        on_delete=models.CASCADE,
        related_name="output_interface_usages",
        help_text="The action this usage is for",
    )
    interface = models.ForeignKey(
        "Interface",
        on_delete=models.CASCADE,
        related_name="output_usages",
        help_text="The interface this usage is for",
    )
    port_index = models.IntegerField(help_text="The index of the port this structure is used for")
    port_key = models.CharField(max_length=2000, help_text="The key of the port this structure is used for")
    modifiers = models.JSONField(default=list)
