"""Filters and orders for actions."""

from __future__ import annotations

import datetime
from typing import Optional

import strawberry
import strawberry_django
from django.db.models import Max, Q
from rekuest_core import enums as renums
from strawberry import auto
from strawberry.types import Info
from strawberry_django.fields.filter_order import filter_field
from strawberry_django.filters import FilterLookup

from facade import inputs, managers, models


@strawberry_django.order_type(models.Action)
class ActionOrder:
    defined_at: auto

    @strawberry_django.order_field
    def used_at(self, info: Info, queryset, value: strawberry_django.Ordering, prefix: str):
        if not value:
            return queryset, []
        queryset = queryset.annotate(latest_assignation_time=Max(f"{prefix}assignation__created_at"))
        return queryset, [value.resolve("latest_assignation_time")]


@strawberry_django.filter_type(models.Action)
class ActionFilter:
    name: Optional[FilterLookup[str]]

    @filter_field
    def search(self, info: Info, queryset, value: str, prefix: str):
        return queryset.filter(**{f"{prefix}name__icontains": value}), Q()

    @filter_field
    def ids(self, info: Info, queryset, value: list[strawberry.ID], prefix: str):
        return queryset.filter(**{f"{prefix}id__in": value}), Q()

    @filter_field
    def demands(self, info: Info, queryset, value: list[inputs.PortDemandInput], prefix: str):
        if len(value) == 0:
            return queryset, Q()

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
    def protocols(self, info: Info, queryset, value: list[str], prefix: str):
        return queryset.filter(**{f"{prefix}protocols__name__in": value}), Q()

    @filter_field
    def kind(self, info: Info, queryset, value: renums.ActionKind, prefix: str):
        return queryset.filter(**{f"{prefix}kind": value}), Q()

    @filter_field
    def in_collection(self, info: Info, queryset, value: str, prefix: str):
        return queryset.filter(**{f"{prefix}collections__name": value}), Q()

    @filter_field
    def used_before(self, info: Info, queryset, value: datetime.datetime, prefix: str):
        return queryset.filter(**{f"{prefix}assignations__created_at__lt": value}), Q()

    @filter_field
    def used_after(self, info: Info, queryset, value: datetime.datetime, prefix: str):
        return queryset.filter(**{f"{prefix}assignations__created_at__gt": value}), Q()

    @filter_field
    def stateful(self, info: Info, queryset, value: bool, prefix: str):
        return queryset.filter(**{f"{prefix}stateful": value}), Q()

    @filter_field(description="Filter using app identifier")
    def app_identifier(self, info: Info, queryset, value: str, prefix: str):
        return queryset.filter(**{f"{prefix}app__identifier": value}), Q()
