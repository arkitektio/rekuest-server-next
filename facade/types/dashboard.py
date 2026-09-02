"""Dashboards, dashboard placements and UI catalogs."""

from __future__ import annotations

import strawberry
import strawberry_django

from facade import filters, models
from facade.types.base import build_prescoped_queryset
from rekuest_core.objects import models as rmodels
from rekuest_core.objects import types as rtypes


@strawberry_django.type(models.Dashboard)
class Dashboard:
    id: strawberry.ID
    name: str | None
    placements: list["DashboardPlacement"]

    @classmethod
    def get_queryset(cls, queryset, info, **kwargs):
        return build_prescoped_queryset(info, queryset, field="organization")


@strawberry_django.type(models.UICatalog, description="A UI catalog: the components a UI app can render and the pure operations it can evaluate for UtilCalls, registered per organization.")
class UICatalog:
    id: strawberry.ID
    name: str
    description: str | None
    bloks: list["Blok"] = strawberry_django.field(description="Bloks rendered against this catalog.")

    @strawberry_django.field(description="Registered components. Empty until a UI app registers the catalog.")
    def components(self) -> list[rtypes.CatalogComponent]:
        return [rmodels.CatalogComponentModel(**component) for component in self.components]

    @strawberry_django.field(description="Registered pure operations UtilCalls may name. Empty until a UI app registers the catalog.")
    def operations(self) -> list[rtypes.CatalogOperation]:
        return [rmodels.CatalogOperationModel(**operation) for operation in self.operations]

    @strawberry_django.field(description="Whether a UI app has registered components or operations; unregistered catalogs validate nothing.")
    def is_registered(self) -> bool:
        return self.is_registered

    @classmethod
    def get_queryset(cls, queryset, info, **kwargs):
        return build_prescoped_queryset(info, queryset, field="organization")


@strawberry_django.type(
    models.DashboardPlacement,
    filters=filters.DashboardPlacementFilter,
    ordering=filters.DashboardPlacementOrder,
    pagination=True,
    description="A placement of an agent in a space.",
)
class DashboardPlacement:
    id: strawberry.ID
    dashboard: Dashboard
    blok: MaterializedBlok | None
