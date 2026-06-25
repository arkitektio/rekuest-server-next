"""Filters for structures, interfaces and their usages."""

from __future__ import annotations

import strawberry
import strawberry_django
from django.db.models import Q
from strawberry.types import Info
from strawberry_django.fields.filter_order import filter_field

from facade import models


@strawberry_django.filter_type(models.StructurePackage)
class StructurePackageFilter:
    @filter_field
    def ids(self, info: Info, queryset, value: list[strawberry.ID], prefix: str):
        return queryset.filter(**{f"{prefix}id__in": value}), Q()

    @filter_field
    def search(self, info: Info, queryset, value: str, prefix: str):
        return queryset.filter(Q(**{f"{prefix}key__icontains": value}) | Q(**{f"{prefix}description__icontains": value})), Q()


@strawberry_django.filter_type(models.Structure)
class StructureFilter:
    @filter_field
    def ids(self, info: Info, queryset, value: list[strawberry.ID], prefix: str):
        return queryset.filter(**{f"{prefix}id__in": value}), Q()

    @filter_field
    def search(self, info: Info, queryset, value: str, prefix: str):
        return queryset.filter(Q(**{f"{prefix}key__icontains": value}) | Q(**{f"{prefix}description__icontains": value})), Q()


@strawberry_django.filter_type(models.Interface)
class InterfaceFilter:
    @filter_field
    def ids(self, info: Info, queryset, value: list[strawberry.ID], prefix: str):
        return queryset.filter(**{f"{prefix}id__in": value}), Q()

    @filter_field
    def search(self, info: Info, queryset, value: str, prefix: str):
        return queryset.filter(Q(**{f"{prefix}key__icontains": value}) | Q(**{f"{prefix}description__icontains": value})), Q()


@strawberry_django.filter_type(models.InputInterfaceUsage)
class InputInterfaceUsageFilter:
    @filter_field
    def ids(self, info: Info, queryset, value: list[strawberry.ID], prefix: str):
        return queryset.filter(**{f"{prefix}id__in": value}), Q()

    @filter_field
    def interface(self, info: Info, queryset, value: strawberry.ID, prefix: str):
        return queryset.filter(**{f"{prefix}interface__id": value}), Q()


@strawberry_django.filter_type(models.OutputInterfaceUsage)
class OutputInterfaceUsageFilter:
    @filter_field
    def ids(self, info: Info, queryset, value: list[strawberry.ID], prefix: str):
        return queryset.filter(**{f"{prefix}id__in": value}), Q()

    @filter_field
    def interface(self, info: Info, queryset, value: strawberry.ID, prefix: str):
        return queryset.filter(**{f"{prefix}interface__id": value}), Q()


@strawberry_django.filter_type(models.InputStructureUsage)
class InputStructureUsageFilter:
    @filter_field
    def ids(self, info: Info, queryset, value: list[strawberry.ID], prefix: str):
        return queryset.filter(**{f"{prefix}id__in": value}), Q()

    @filter_field
    def structure(self, info: Info, queryset, value: strawberry.ID, prefix: str):
        return queryset.filter(**{f"{prefix}structure__id": value}), Q()


@strawberry_django.filter_type(models.OutputStructureUsage)
class OutputStructureUsageFilter:
    @filter_field
    def ids(self, info: Info, queryset, value: list[strawberry.ID], prefix: str):
        return queryset.filter(**{f"{prefix}id__in": value}), Q()

    @filter_field
    def structure(self, info: Info, queryset, value: strawberry.ID, prefix: str):
        return queryset.filter(**{f"{prefix}structure__id": value}), Q()
