"""Inputs for dashboards."""

import strawberry


@strawberry.input(description="Input for creating a dashboard, optionally specifying its name, the bloks to include, and the owning organization.")
class CreateDashboardInput:
    name: str = strawberry.field(description="The name of the dashboard.")
    bloks: list[str] = strawberry.field(default_factory=list, description="The list of blok IDs to include in the dashboard.")
    organization: str | None = strawberry.field(default=None, description="The organization ID to associate with the dashboard.")


@strawberry.input(description="Input for deleting a dashboard. This is used to delete a dashboard by its ID.")
class DeleteDashboardInput:
    id: strawberry.ID = strawberry.field(description="The ID of the dashboard to delete.")


@strawberry.input(description="Input for updating a dashboard. This is used to update the properties of a dashboard, such as its name, associated bloks, or organization.")
class UpdateDashboardInput:
    id: strawberry.ID = strawberry.field(description="The ID of the dashboard to update.")
    name: str | None = strawberry.field(default=None, description="The new name of the dashboard.")
    bloks: list[str] | None = strawberry.field(default=None, description="The new list of blok IDs to include in the dashboard. This will replace the existing list if provided.")
    organization: str | None = strawberry.field(default=None, description="The new organization ID to associate with the dashboard.")
