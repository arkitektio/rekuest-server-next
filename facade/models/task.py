import uuid

from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.indexes import GinIndex
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
    is_higher_order_child = models.BooleanField(
        default=False,
        help_text="Whether this task is the lower child of a higher-order wrapper — its yields/terminals unfold onto the wrapper. Lets the event hot path skip the parent lookup for ordinary tasks.",
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
    args_hash = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        db_index=True,
        help_text="Canonical sha256 of the assign args (provenance canonicalization v1) — the replay-discovery key",
    )
    dependencies = models.JSONField(blank=True, null=True, help_text="The Args", default=dict)
    caller = models.ForeignKey(
        "Caller",
        on_delete=models.CASCADE,
        help_text="The caller (client/user/organization) that created this Task",
        null=True,
        blank=True,
        related_name="tasks",
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
        indexes = [
            # The org-scoped ``tasks`` list. The org restriction lives on Agent (see
            # ``types.Task.get_queryset`` -> ``agent__organization``), so this is the Task-side
            # half of that join; it doubles as the ``agent`` filter and supplies the default
            # ``-created_at`` ordering and the created_before/after range without a sort node.
            models.Index(fields=["agent", "-created_at"], name="task_agent_created_idx"),
            # ``TaskFilter.state`` (latest_event_kind__in) org-wide, with the same ordering.
            # Leading with a ~16-value column is fine because the second column is the sort key.
            models.Index(fields=["latest_event_kind", "-created_at"], name="task_state_created_idx"),
            # ``TaskFilter.acted_on`` uses ``acted_on__overlap`` (``&&``) on an ArrayField. A btree
            # cannot answer overlap at all, so GIN is the only index type that avoids a seq scan.
            GinIndex(fields=["acted_on"], name="task_acted_on_gin_idx"),
            # ``queries.my_tasks``: filter(caller=, root__isnull=True, is_done=False)
            # .order_by("-created_at"). Both booleans are constants of that query, so they belong
            # in the condition — the partial index only ever holds the small live-root set.
            models.Index(
                fields=["caller", "-created_at"],
                condition=models.Q(root__isnull=True, is_done=False),
                name="task_my_root_open_idx",
            ),
            # ``queries.reusable_task_for``: args_hash is the selective key, the action ids come
            # from the Action-side hash/pure/organization predicate, ``-finished_at`` is the sort.
            models.Index(
                fields=["args_hash", "action", "-finished_at"],
                condition=models.Q(is_done=True, ephemeral=False, latest_event_kind=enums.TaskEventChoices.COMPLETED),
                name="task_replay_idx",
            ),
            # The agent-disconnect and orphaned-executor sweeps (``ModelPersistBackend``,
            # ``reconcile_tasks``) all run filter(agent_id=, is_done=False). A partial index holds
            # only in-flight rows instead of walking that agent's whole history.
            models.Index(fields=["agent"], condition=models.Q(is_done=False), name="task_agent_open_idx"),
            # The assign dedupe — filter(caller=, reference=) — on the hottest write path.
            models.Index(fields=["caller", "reference"], name="task_caller_ref_idx"),
            # The retention sweep: filter(is_done=True, root__isnull=True, finished_at__lt=cutoff).
            # Partial on exactly those constants so it only ever holds terminal roots.
            models.Index(
                fields=["finished_at"],
                condition=models.Q(is_done=True, root__isnull=True),
                name="task_retention_idx",
            ),
        ]


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
        choices_enum=enums.LogLevelChoices,
        help_text="The log level (LOG events)",
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
