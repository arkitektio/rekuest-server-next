import uuid

from django.contrib.postgres.fields import ArrayField
from django.db import models
from django_choices_field import TextChoicesField

from facade import enums


class Task(models.Model):
    """A constant log of a tasks transition through finding a Action, Implementation and finally Pod , also a store for its results"""

    acted_on = ArrayField(base_field=models.CharField(max_length=1000), help_text="Which structures were acted on in this task", default=list)
    implementation = models.ForeignKey(
        "Implementation",
        on_delete=models.CASCADE,
        help_text="Which implementation is the task currently mapped (can be reassigned)?",
        related_name="tasks",
        blank=True,
        null=True,
    )
    resolution = models.ForeignKey(
        "Resolution",
        on_delete=models.CASCADE,
        help_text="The resolution used for this task",
        related_name="tasks",
        blank=True,
        null=True,
    )
    action = models.ForeignKey("Action", on_delete=models.CASCADE, help_text="The action this was assigned to", related_name="tasks")
    ephemeral = models.BooleanField(
        default=False,
        help_text="Is this Task ephemeral (e.g. should it be deleted after its done or should it be kept for future reference)",
    )
    hooks = models.JSONField(
        default=list,
        help_text="hooks that are tight to the lifecycle of this task",
    )
    reference = models.CharField(
        max_length=1000,
        default=uuid.uuid4,
        help_text="The Unique identifier of this Task considering its parent",
    )
    dependency = models.CharField(
        max_length=1000,
        null=True,
        blank=True,
        help_text="The reference of the dependency this task was assigned to (e.g. imagej)",
        default="general",
    )
    dependency_method = models.CharField(
        max_length=1000,
        null=True,
        blank=True,
        help_text="The action of the dependency this task was assigned to (e.g. imagej.fft )",
    )
    capture = models.BooleanField(
        default=False,
        help_text="Should we capture the logs and events of this Task (e.g. for debugging or auditing purposes)?",
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="The Tasks parent (the one that created this (none if there is no parent))",
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
    caller = models.ForeignKey(
        "Caller",
        on_delete=models.CASCADE,
        help_text="The caller (client/user/organization) that created this Task",
        null=True,
        blank=True,
        related_name="tasks",
    )
    originating_connection_id = models.CharField(
        max_length=1000,
        null=True,
        blank=True,
        help_text="The websocket connection id that originated this (root) task over the agent socket. Identifies which live connection's death should cascade-cancel it. Null for GraphQL-originated or non-root tasks.",
    )
    originating_session_id = models.CharField(
        max_length=1000,
        null=True,
        blank=True,
        help_text="The caller's process session id (volatile, in-memory) at origination. Lets a reconnect with the same session reclaim instead of cascade-cancelling. Null for GraphQL-originated or non-root tasks.",
    )
    agent = models.ForeignKey(
        "Agent",
        on_delete=models.CASCADE,
        max_length=1000,
        help_text="This Task app",
        related_name="tasks",
    )
    latest_event_kind = TextChoicesField(
        max_length=1000,
        choices_enum=enums.TaskEventChoices,
        help_text="The latest Status of this Provision (transitioned by events)",
    )
    latest_instruct_kind = TextChoicesField(
        max_length=1000,
        choices_enum=enums.TaskInstructChoices,
        help_text="The latest Instruct of this Provision (transitioned by events)",
    )
    statusmessage = models.CharField(
        max_length=1000,
        help_text="Clear Text status of the Provision as for now",
        blank=True,
    )
    is_done = models.BooleanField(
        default=False,
        help_text="Is this Task done (e.g. has it been completed and resulted in an error?)",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.latest_event_kind} for {self.action_id}"

    class Meta:
        pass


class TaskEvent(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    task = models.ForeignKey(
        Task,
        help_text="The task this log item belongs to",
        related_name="events",
        on_delete=models.CASCADE,
    )
    delegated_to = models.ForeignKey(
        Task,
        help_text="If this event was delegated to another task, which one?",
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
        help_text="The progress of the task (0-100) (set for yield events)",
        null=True,
        blank=True,
    )
    message = models.CharField(max_length=30000, null=True, blank=True)
    # Status Field
    kind = TextChoicesField(
        max_length=1000,
        choices_enum=enums.TaskEventChoices,
        help_text="The event kind",
    )
    level = TextChoicesField(
        max_length=1000,
        choices_enum=enums.TaskEventChoices,
        help_text="The log level",
        null=True,
        blank=True,
    )


class TaskInstruct(models.Model):
    caller = models.ForeignKey(
        "Caller",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="Which caller created this Instruction (if any?)",
        related_name="task_instructs",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    task = models.ForeignKey(
        Task,
        help_text="The task this log item belongs to",
        related_name="instructs",
        on_delete=models.CASCADE,
    )
    # Status Field
    kind = TextChoicesField(
        max_length=1000,
        choices_enum=enums.TaskInstructChoices,
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
