"""Task types, their statistics resolver, events and instructs."""

from __future__ import annotations

import datetime
from typing import List, Optional

import strawberry
import strawberry_django
from rekuest_core import scalars as rscalars

from facade import enums, filters, models, scalars
from facade.type_gen import create_stats_type
from facade.types.base import build_prescoped_queryset, build_prescoper
from facade.types.dependency import ResolvedAgentDependency


@strawberry_django.type(models.Task, filters=filters.TaskFilter, ordering=filters.TaskOrder, pagination=True, description="Tracks the assignment of an implementation to a specific task.")
class Task:
    id: strawberry.ID = strawberry_django.field(description="Unique ID of the task.")
    reference: str | None = strawberry_django.field(description="Optional external reference for tracking.")
    is_done: bool = strawberry_django.field(description="Indicates if the task is completed.")
    args: rscalars.AnyDefault = strawberry_django.field(description="Arguments used in the task.")
    dependencies: rscalars.AnyDefault = strawberry_django.field(description="The used dependencies for this assignemnet")
    resolution: Optional["Resolution"] = strawberry.field(description="Resolution used to resolve dependencies for this task.")
    root: Optional["Task"] = strawberry.field(description="Root task in the creation chain.")
    parent: Optional["Task"] = strawberry.field(description="Parent task that triggered this one.")
    action: "Action" = strawberry.field(description="Action assigned.")
    capture: bool = strawberry.field(description="Indicates if the task is being captured for logging or debugging.")
    implementation: "Implementation" = strawberry.field(description="Implementation assigned to execute.")
    latest_event_kind: enums.TaskEventKind = strawberry.field(description="Type of the latest event.")
    latest_instruct_kind: enums.TaskInstructKind = strawberry.field(description="Last instruction type.")
    caller: Optional["Caller"] = strawberry.field(description="Caller that created this task.")
    created_at: datetime.datetime = strawberry_django.field(description="Creation timestamp.")
    updated_at: datetime.datetime = strawberry_django.field(description="Last update timestamp.")
    finished_at: datetime.datetime | None = strawberry.field(description="Timestamp when the task was finished.")
    acted_on: List[str] = strawberry.field(description="List of resources or entities this task acted upon.")
    ephemeral: bool = strawberry.field(description="Indicates if the task should be deleted after completion.")
    children: List["Task"] = strawberry.field(description="Child tasks spawned from this one.")
    agent: Agent | None = strawberry.field(description="Agent responsible for this task.")
    events: list["TaskEvent"] = strawberry_django.field(description="The events")
    dependency: str | None = strawberry_django.field(description="The dependency thats linked to the parents execution if applicable.")
    dependency_method: str | None = strawberry_django.field(description="The method of the dependency that caused this task, if applicable.")
    resolved_dependencies: list["ResolvedAgentDependency"] = strawberry_django.field(description="The resolved dependencies for this task.")

    @strawberry_django.field(description="List of recent instructions for this task.")
    def instructs(self) -> list["TaskInstruct"]:
        return self.instructs.order_by("-created_at")[:10]

    @strawberry_django.field(description="Get a specific argument by key.")
    def arg(self, key: str) -> scalars.Args | None:
        return self.args.get(key, None)

    @strawberry_django.field(description="Get a specific dependency by key.")
    def resolved_dependencies(self) -> List[ResolvedAgentDependency]:
        resolved = []
        for key, item in self.dependencies.items():
            print("Processing dependency:", key, item)
            resolved.append(ResolvedAgentDependency(_key=key, _value=item))
        return resolved

    @classmethod
    def get_queryset(cls, queryset, info, **kwargs):
        return build_prescoped_queryset(info, queryset, field="implementation__action__organization")


TaskStats, TaskStatsResolver = create_stats_type(
    models.Task,
    filters=filters.TaskFilter,
    allowed_fields={
        "created_at": "created_at",
    },
    allowed_datetime_fields={"created_at": "created_at"},
    prescope=build_prescoper(field="agent__organization"),
)


@strawberry_django.type(models.TaskEvent, filters=filters.TaskEventFilter, ordering=filters.TaskEventOrder, pagination=True, description="An event that occurred during a task.")
class TaskEvent:
    id: strawberry.ID = strawberry_django.field(description="Unique ID of the event.")
    name: str = strawberry_django.field(description="Name of the event.")
    returns: rscalars.AnyDefault | None = strawberry_django.field(description="Optional return values.")
    task: "Task" = strawberry_django.field(description="Associated task.")
    kind: enums.TaskEventKind = strawberry_django.field(description="Kind of task event.")
    message: str | None = strawberry_django.field(description="Optional message associated with the event.")
    progress: int | None = strawberry_django.field(description="Progress percentage.")
    created_at: strawberry.auto = strawberry_django.field(description="Time when event was created.")
    delegated_to: Optional["Task"] = strawberry_django.field(description="If this event was delegated, the task it was delegated to.")

    @strawberry_django.field(description="Default log level.")
    def level(self) -> enums.LogLevel:
        return self.level or enums.LogLevel.INFO

    @strawberry_django.field(description="Reference string for the event.")
    def reference(self) -> str:
        return self.task.reference


@strawberry_django.type(models.TaskInstruct, filters=filters.TaskEventFilter, pagination=True, description="An instruct event for a specific task.")
class TaskInstruct:
    id: strawberry.ID = strawberry_django.field(description="Unique ID of the instruct event.")
    task: "Task" = strawberry_django.field(description="Task the instruction relates to.")
    kind: enums.TaskInstructKind = strawberry_django.field(description="Type of instruction.")
    created_at: strawberry.auto = strawberry_django.field(description="Time when instruction was issued.")
