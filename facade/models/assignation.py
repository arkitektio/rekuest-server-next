import uuid

from django.contrib.postgres.fields import ArrayField
from django.db import models
from django_choices_field import TextChoicesField

from facade import enums


class Assignation(models.Model):
    """A constant log of a tasks transition through finding a Action, Implementation and finally Pod , also a store for its results"""

    waiter = models.ForeignKey("Waiter", on_delete=models.CASCADE, help_text="Which Waiter assigned this?")
    reservation = models.ForeignKey(
        "Reservation",
        on_delete=models.CASCADE,
        help_text="Was this assigned through a reservation?",
        related_name="assignations",
        blank=True,
        null=True,
    )
    acted_on = ArrayField(base_field=models.CharField(max_length=1000), help_text="Which structures were acted on in this assignation", default=list)
    implementation = models.ForeignKey(
        "Implementation",
        on_delete=models.CASCADE,
        help_text="Which implementation is the assignation currently mapped (can be reassigned)?",
        related_name="assignations",
        blank=True,
        null=True,
    )
    resolution = models.ForeignKey(
        "Resolution",
        on_delete=models.CASCADE,
        help_text="The resolution used for this assignation",
        related_name="assignations",
        blank=True,
        null=True,
    )
    action = models.ForeignKey("Action", on_delete=models.CASCADE, help_text="The action this was assigned to", related_name="assignations")
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
    dependency = models.CharField(
        max_length=1000,
        null=True,
        blank=True,
        help_text="The reference of the dependency this assignation was assigned to (e.g. imagej)",
        default="general",
    )
    dependency_method = models.CharField(
        max_length=1000,
        null=True,
        blank=True,
        help_text="The action of the dependency this assignation was assigned to (e.g. imagej.fft )",
    )
    capture = models.BooleanField(
        default=False,
        help_text="Should we capture the logs and events of this Assignation (e.g. for debugging or auditing purposes)?",
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
    dependencies = models.JSONField(blank=True, null=True, help_text="The Args", default=dict)
    waiter = models.ForeignKey(
        "Waiter",
        on_delete=models.CASCADE,
        max_length=1000,
        help_text="This Assignation app",
        null=True,
        blank=True,
        related_name="assignations",
    )
    agent = models.ForeignKey(
        "Agent",
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
    finished_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.latest_event_kind} for {self.reservation}"

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
    delegated_to = models.ForeignKey(
        Assignation,
        help_text="If this event was delegated to another assignation, which one?",
        related_name="delegated_events",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
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
        "Waiter",
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
        "Agent",
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
