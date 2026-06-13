"""Filters and orders for protocols, toolboxes and shortcuts."""

from __future__ import annotations

from typing import Optional

import strawberry
import strawberry_django
from django.db.models import Q
from rekuest_core import enums as renums
from strawberry import auto
from strawberry.types import Info
from strawberry_django.fields.filter_order import filter_field
from strawberry_django.filters import FilterLookup

from facade import inputs, managers, models


@strawberry_django.order(models.Protocol)
class ProtocolOrder:
    name: auto


@strawberry_django.order(models.Shortcut)
class ShortcutOrder:
    name: auto


@strawberry_django.order(models.Toolbox)
class ToolboxOrder:
    name: auto


@strawberry_django.filter_type(models.Protocol)
class ProtocolFilter:
    name: Optional[FilterLookup[str]]

    @filter_field
    def ids(self, info: Info, queryset, value: list[strawberry.ID], prefix: str):
        return queryset.filter(**{f"{prefix}id__in": value}), Q()

    @filter_field
    def search(self, info: Info, queryset, value: str, prefix: str):
        return queryset.filter(**{f"{prefix}name__icontains": value}), Q()


@strawberry_django.filter_type(models.Toolbox)
class ToolboxFilter:
    name: Optional[FilterLookup[str]]

    @filter_field
    def ids(self, info: Info, queryset, value: list[strawberry.ID], prefix: str):
        return queryset.filter(**{f"{prefix}id__in": value}), Q()

    @filter_field
    def search(self, info: Info, queryset, value: str, prefix: str):
        return queryset.filter(**{f"{prefix}name__icontains": value}), Q()


@strawberry_django.filter_type(models.Action)
class ShortcutActionFilter:
    @filter_field
    def search(self, info: Info, queryset, value: str, prefix: str):
        return queryset.filter(**{f"{prefix}name__icontains": value}), Q()

    @filter_field
    def name(self, info: Info, queryset, value: str, prefix: str):
        return queryset.filter(**{f"{prefix}name": value}), Q()

    @filter_field
    def ids(self, info: Info, queryset, value: list[strawberry.ID], prefix: str):
        return queryset.filter(**{f"{prefix}id__in": value}), Q()

    @filter_field
    def demands(self, info: Info, queryset, value: list[inputs.PortDemandInput], prefix: str):
        filtered_ids = None

        for ports_demand in value:
            new_ids = managers.get_action_ids_by_demands(
                ports_demand.matches,
                type=ports_demand.kind.value,
                force_length=ports_demand.force_length,
                force_non_nullable_length=ports_demand.force_non_nullable_length,
                force_structure_length=ports_demand.force_structure_length,
            )

            if filtered_ids is None:
                filtered_ids = set(new_ids)
            else:
                filtered_ids = filtered_ids.intersection(new_ids)

        if filtered_ids is None:
            return queryset, Q()

        return queryset.filter(**{f"{prefix}id__in": filtered_ids}), Q()

    @filter_field
    def kind(self, info: Info, queryset, value: renums.ActionKind, prefix: str):
        return queryset.filter(**{f"{prefix}kind": value}), Q()

    @filter_field
    def protocols(self, info: Info, queryset, value: list[str], prefix: str):
        return queryset.filter(**{f"{prefix}protocols__name__in": value}), Q()


@strawberry_django.filter_type(models.Shortcut)
class ShortcutFilter:
    @filter_field
    def search(self, info: Info, queryset, value: str, prefix: str):
        return queryset.filter(**{f"{prefix}name__icontains": value}), Q()

    @filter_field
    def ids(self, info: Info, queryset, value: list[strawberry.ID], prefix: str):
        return queryset.filter(**{f"{prefix}id__in": value}), Q()

    @filter_field
    def demands(self, info: Info, queryset, value: list[inputs.PortDemandInput], prefix: str):
        filtered_ids = None

        for ports_demand in value:
            new_ids = managers.get_action_ids_by_demands(
                ports_demand.matches,
                type=ports_demand.kind.value,
                force_length=ports_demand.force_length,
                force_non_nullable_length=ports_demand.force_non_nullable_length,
                force_structure_length=ports_demand.force_structure_length,
                model="facade_shortcut",
            )

            if filtered_ids is None:
                filtered_ids = set(new_ids)
            else:
                filtered_ids = filtered_ids.intersection(new_ids)

        if filtered_ids is None:
            return queryset, Q()

        return queryset.filter(**{f"{prefix}id__in": filtered_ids}), Q()

    @filter_field
    def toolbox(self, info: Info, queryset, value: strawberry.ID, prefix: str):
        return queryset.filter(**{f"{prefix}toolbox_id": value}), Q()
