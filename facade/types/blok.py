"""Bloks, blok dependencies, materialized bloks and agent mappings."""

from __future__ import annotations

import datetime

import strawberry
import strawberry_django
from rekuest_core.objects import models as rmodels
from rekuest_core.objects import types as rtypes

from facade import filters, models, scalars
from facade.types.demand import ActionDependencyModel, StateDependencyModel


@strawberry_django.type(models.Blok)
class Blok:
    id: strawberry.ID
    name: str
    description: str | None
    creator: User
    catalog: UICatalog
    materialized_bloks: list["MaterializedBlok"] = strawberry_django.field(
        description="Materialized bloks that are instances of this blok.",
    )
    dependencies: list["BlokDependency"] = strawberry_django.field(
        description="Dependencies that need to be resolved for this blok.",
    )

    @strawberry_django.field(description="List of action demands specified in this blok.")
    def components(self) -> list[rtypes.ComponentNode]:
        return [rmodels.ComponentNodeModel(**i) for i in self.components]

    @strawberry_django.field(description="List of action demands specified in this blok.")
    def ui_components(self) -> scalars.Props:
        return self.components

    @strawberry_django.field(description="List of action demands specified in this blok.")
    def demo_state(self) -> scalars.Props:
        return self.demo_state


@strawberry_django.type(models.BlokDependency, filters=filters.BlokDependencyFilter, pagination=True, description="Represents a dependency between implementations and actions.")
class BlokDependency:
    id: strawberry.ID = strawberry_django.field(description="Unique ID of the dependency.")
    implementation: "Implementation" = strawberry_django.field(description="The implementation this dependency belongs to.")
    key: str = strawberry_django.field(description="Optional string identifier or tag for reference.")
    optional: bool = strawberry_django.field(description="Indicates if the dependency is optional.")
    description: str | None = strawberry_django.field(description="Optional description of the dependency.")
    auto_resolvable: bool = strawberry.field(
        default=False,
        description="Whether this dependency is auto resolvable or not. If so we will try to automatically resolve it based on the demands specified in the dependency and the capabilities of the available agents in the system. This is used to identify the demand in the system. Attention if any of the dependencies of this agent dependency is not auto resolvable, this dependency will also not be auto resolvable",
    )
    app_filter: str | None = strawberry_django.field(
        default=None,
        description="Optional filter string to limit which agents can be bound to this dependency based on the app they belong to. The filter string should be in the format 'app_identifier:version' where version can be a specific version or a wildcard '*'. For example, 'my_app:*' would allow any agent belonging to 'my_app' regardless of version, while 'my_app:1.0.0' would only allow agents with that specific version.",
    )
    version_filter: str | None = strawberry_django.field(
        default=None,
        description="Optional filter string to limit which agents can be bound to this dependency based on the version of the app they belong to. The filter string should be in the format 'version' where version can be a specific version or a wildcard '*'. For example, '*' would allow any version, while '1.0.0' would only allow agents with that specific version.",
    )
    min_viable_instances: int | None = strawberry_django.field(
        default=None,
        description="Minimum number of viable agent instances required to resolve this dependency. This is used in combination with the auto_resolvable field to determine if a dependency can be automatically resolved. If the number of available agent instances that match the filters is less than this number, the dependency will not be considered auto resolvable.",
    )
    max_viable_instances: int | None = strawberry_django.field(
        default=None,
        description="Maximum number of viable agent instances that can be bound to this dependency. This is used in combination with the auto_resolvable field to determine if a dependency can be automatically resolved. If the number of available agent instances that match the filters is greater than this number, the dependency will not be considered auto resolvable.",
    )

    @strawberry_django.field(description="List of action demands specified in this dependency.")
    def singular(self) -> bool:
        """Whether this dependency is singular or not. A singular dependency is a dependency that can only be resolved to one agent, meaning that if there are multiple implementations that match the filters and demands of this dependency, it will not be considered singular."""
        return self.min_viable_instances == 1 and (self.max_viable_instances is None or self.max_viable_instances == 1)

    @strawberry_django.field(description="The named action requirements of this dependency.")
    def action_dependencies(self) -> list["ActionDependency"]:
        # get_action_dependencies normalizes legacy flat JSON into the demand wrapper.
        return [ActionDependencyModel(**d.model_dump()) for d in self.get_action_dependencies()]

    @strawberry_django.field(description="The named state requirements of this dependency.")
    def state_dependencies(self) -> list["StateDependency"]:
        return [StateDependencyModel(**d.model_dump()) for d in self.get_state_dependencies()]


@strawberry_django.type(models.MaterializedBlok, filters=filters.MaterializedBlokFilter, pagination=True, ordering=filters.MaterializedBlokOrder, description="A materialized instance of a Blok that can be placed on dashboards and linked to agent states.")
class MaterializedBlok:
    id: strawberry.ID
    blok: Blok
    name: str | None
    description: str | None
    created_at: datetime.datetime
    updated_at: datetime.datetime
    agent_mappings: list["BlokAgentMapping"] = strawberry_django.field(
        description="Mappings of states to this materialized blok.",
    )
    dashboard_placements: list["DashboardPlacement"] = strawberry_django.field(
        description="Placements of this materialized blok on dashboards.",
    )
    placements: list["Placement"] = strawberry_django.field(
        description="Placements of this materialized blok.",
    )


@strawberry_django.type(models.BlokAgentMapping)
class BlokAgentMapping:
    id: strawberry.ID
    key: str
    agent: Agent

    materialized_blok: MaterializedBlok
    created_at: datetime.datetime
    updated_at: datetime.datetime
