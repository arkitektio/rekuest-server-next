"""Filters and orders for memory/filesystem shelves and drawers."""

from __future__ import annotations

import strawberry
import strawberry_django
from django.db.models import Q
from strawberry import auto
from strawberry.types import Info
from strawberry_django.fields.filter_order import filter_field

from facade import models


@strawberry_django.filter_type(models.FilesystemShelve, description="A way to filter shelved items")
class FilesystemShelveFilter:
    @filter_field
    def ids(self, info: Info, queryset, value: list[strawberry.ID], prefix: str):
        return queryset.filter(**{f"{prefix}id__in": value}), Q()


@strawberry_django.filter_type(models.MemoryShelve, description="A way to filter shelved items")
class MemoryShelveFilter:
    agent: strawberry.ID | None

    @filter_field
    def ids(self, info: Info, queryset, value: list[strawberry.ID], prefix: str):
        return queryset.filter(**{f"{prefix}id__in": value}), Q()


@strawberry_django.order(models.MemoryShelve)
class MemoryShelveOrder:
    name: auto


@strawberry_django.filter_type(models.FileDrawer, description="A way to filter shelved items")
class FileDrawerFilter:
    shelve: strawberry.ID | None
    agent: strawberry.ID | None
    identifier: str | None

    @filter_field
    def ids(self, info: Info, queryset, value: list[strawberry.ID], prefix: str):
        return queryset.filter(**{f"{prefix}id__in": value}), Q()


@strawberry_django.filter_type(models.MemoryDrawer, description="A way to filter shelved items")
class MemoryDrawerFilter:
    shelve: strawberry.ID | None
    agent: strawberry.ID | None

    @filter_field
    def implementation(self, info: Info, queryset, value: strawberry.ID, prefix: str):
        return queryset.filter(**{f"{prefix}shelve__agent__implementations": value}), Q()

    @filter_field
    def identifier(self, info: Info, queryset, value: str, prefix: str):
        return queryset.filter(**{f"{prefix}identifier": value}), Q()

    @filter_field
    def ids(self, info: Info, queryset, value: list[strawberry.ID], prefix: str):
        return queryset.filter(**{f"{prefix}id__in": value}), Q()

    @filter_field
    def search(self, info: Info, queryset, value: str, prefix: str):
        return queryset.filter(**{f"{prefix}label__icontains": value}), Q()
