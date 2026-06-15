"""Assignation types, their statistics resolver, events and instructs."""

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


@strawberry_django.type(models.Assignation, filters=filters.AssignationFilter, ordering=filters.AssignationOrder, pagination=True, description="Tracks the assignment of an implementation to a specific task.")
class Assignation:
    id: strawberry.ID = strawberry_django.field(description="Unique ID of the assignation.")
    reference: str | None = strawberry_django.field(description="Optional external reference for tracking.")
    is_done: bool = strawberry_django.field(description="Indicates if the assignation is completed.")
    args: rscalars.AnyDefault = strawberry_django.field(description="Arguments used in the assignation.")
    dependencies: rscalars.AnyDefault = strawberry_django.field(description="The used dependencies for this assignemnet")
    resolution: Optional["Resolution"] = strawberry.field(description="Resolution used to resolve dependencies for this assignation.")
    root: Optional["Assignation"] = strawberry.field(description="Root assignation in the creation chain.")
    parent: Optional["Assignation"] = strawberry.field(description="Parent assignation that triggered this one.")
    reservation: Optional["Reservation"] = strawberry.field(description="Reservation that caused this assignation.")
    action: "Action" = strawberry.field(description="Action assigned.")
    capture: bool = strawberry.field(description="Indicates if the assignation is being captured for logging or debugging.")
    implementation: "Implementation" = strawberry.field(description="Implementation assigned to execute.")
    latest_event_kind: enums.AssignationEventKind = strawberry.field(description="Type of the latest event.")
    latest_instruct_kind: enums.AssignationInstructKind = strawberry.field(description="Last instruction type.")
    status_message: str | None = strawberry_django.field(description="Current status message.")
    caller: Optional["Caller"] = strawberry.field(description="Caller that created this assignation.")
    created_at: datetime.datetime = strawberry_django.field(description="Creation timestamp.")
    updated_at: datetime.datetime = strawberry_django.field(description="Last update timestamp.")
    finished_at: datetime.datetime | None = strawberry.field(description="Timestamp when the assignation was finished.")
    acted_on: List[str] = strawberry.field(description="List of resources or entities this assignation acted upon.")
    ephemeral: bool = strawberry.field(description="Indicates if the assignation should be deleted after completion.")
    children: List["Assignation"] = strawberry.field(description="Child assignations spawned from this one.")
    agent: Agent | None = strawberry.field(description="Agent responsible for this assignation.")
    events: list["AssignationEvent"] = strawberry_django.field(description="The events")
    dependency: str | None = strawberry_django.field(description="The dependency thats linked to the parents execution if applicable.")
    dependency_method: str | None = strawberry_django.field(description="The method of the dependency that caused this assignation, if applicable.")
    resolved_dependencies: list["ResolvedAgentDependency"] = strawberry_django.field(description="The resolved dependencies for this assignation.")

    @strawberry_django.field(description="List of recent instructions for this assignation.")
    def instructs(self) -> list["AssignationInstruct"]:
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


AssignationStats, AssignationStatsResolver = create_stats_type(
    models.Assignation,
    filters=filters.AssignationFilter,
    allowed_fields={
        "created_at": "created_at",
    },
    allowed_datetime_fields={"created_at": "created_at"},
    prescope=build_prescoper(field="agent__organization"),
)


@strawberry_django.type(models.AssignationEvent, filters=filters.AssignationEventFilter, ordering=filters.AssignationEventOrder, pagination=True, description="An event that occurred during an assignation.")
class AssignationEvent:
    id: strawberry.ID = strawberry_django.field(description="Unique ID of the event.")
    name: str = strawberry_django.field(description="Name of the event.")
    returns: rscalars.AnyDefault | None = strawberry_django.field(description="Optional return values.")
    assignation: "Assignation" = strawberry_django.field(description="Associated assignation.")
    kind: enums.AssignationEventKind = strawberry_django.field(description="Kind of assignation event.")
    message: str | None = strawberry_django.field(description="Optional message associated with the event.")
    progress: int | None = strawberry_django.field(description="Progress percentage.")
    created_at: strawberry.auto = strawberry_django.field(description="Time when event was created.")
    delegated_to: Optional["Assignation"] = strawberry_django.field(description="If this event was delegated, the assignation it was delegated to.")

    @strawberry_django.field(description="Default log level.")
    def level(self) -> enums.LogLevel:
        return self.level or enums.LogLevel.INFO

    @strawberry_django.field(description="Reference string for the event.")
    def reference(self) -> str:
        return self.assignation.reference


@strawberry_django.type(models.AssignationInstruct, filters=filters.AssignationEventFilter, pagination=True, description="An instruct event for a specific assignation.")
class AssignationInstruct:
    id: strawberry.ID = strawberry_django.field(description="Unique ID of the instruct event.")
    assignation: "Assignation" = strawberry_django.field(description="Assignation the instruction relates to.")
    kind: enums.AssignationInstructKind = strawberry_django.field(description="Type of instruction.")
    created_at: strawberry.auto = strawberry_django.field(description="Time when instruction was issued.")
