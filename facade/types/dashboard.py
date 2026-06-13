"""Dashboards, dashboard placements and UI catalogs."""

from __future__ import annotations

import strawberry
import strawberry_django

from facade import filters, models


@strawberry_django.type(models.Dashboard)
class Dashboard:
    id: strawberry.ID
    name: str | None
    placements: list["DashboardPlacement"]


@strawberry_django.type(models.UICatalog)
class UICatalog:
    id: strawberry.ID
    name: str
    description: str | None


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
