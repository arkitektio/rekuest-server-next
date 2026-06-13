"""Filters and orders for 3D models, spaces and placements."""

from __future__ import annotations

import strawberry
import strawberry_django
from django.db.models import Q
from strawberry import auto
from strawberry.types import Info
from strawberry_django.fields.filter_order import filter_field

from facade import models


@strawberry_django.order(models.ThreeDModel)
class ThreeDModelOrder:
    created_at: auto
    updated_at: auto
    name: auto


@strawberry_django.filter_type(models.ThreeDModel, description="A way to filter 3D models")
class ThreeDModelFilter:
    @filter_field(description="Filter by IDs")
    def ids(self, info: Info, queryset, value: list[strawberry.ID], prefix: str):
        return queryset.filter(**{f"{prefix}id__in": value}), Q()

    @filter_field(description="Search by name")
    def search(self, info: Info, queryset, value: str, prefix: str):
        return queryset.filter(**{f"{prefix}name__icontains": value}), Q()


@strawberry_django.order(models.Space)
class SpaceOrder:
    created_at: auto
    updated_at: auto
    name: auto


@strawberry_django.filter_type(models.Space, description="A way to filter spaces")
class SpaceFilter:
    @filter_field(description="Filter by IDs")
    def ids(self, info: Info, queryset, value: list[strawberry.ID], prefix: str):
        return queryset.filter(**{f"{prefix}id__in": value}), Q()

    @filter_field(description="Search by name")
    def search(self, info: Info, queryset, value: str | None, prefix: str):
        return queryset.filter(**{f"{prefix}name__icontains": value}), Q()


@strawberry_django.order_type(models.Placement)
class PlacementOrder:
    role: auto
    created_at: auto


@strawberry_django.filter_type(models.Placement, description="A way to filter placements (space memberships)")
class PlacementFilter:
    @filter_field(description="Filter by IDs")
    def ids(self, info: Info, queryset, value: list[strawberry.ID], prefix: str):
        return queryset.filter(**{f"{prefix}id__in": value}), Q()

    @filter_field(description="Filter by space")
    def space(self, info: Info, queryset, value: strawberry.ID, prefix: str):
        return queryset.filter(**{f"{prefix}space_id": value}), Q()

    @filter_field(description="Filter by agent")
    def agent(self, info: Info, queryset, value: strawberry.ID, prefix: str):
        return queryset.filter(**{f"{prefix}agent_id": value}), Q()

    @filter_field(description="Search by name")
    def search(self, info: Info, queryset, value: str | None, prefix: str):
        return queryset.filter(**{f"{prefix}name__icontains": value}), Q()
