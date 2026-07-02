"""Filters and orders for implementations (and the implementation-action filter)."""

from __future__ import annotations

import datetime
from typing import Optional

import strawberry
import strawberry_django
from django.db.models import Q
from django.utils import timezone
from rekuest_core import enums as renums
from rekuest_core import scalars as rscalars
from strawberry import auto
from strawberry.types import Info
from strawberry_django.fields.filter_order import filter_field
from strawberry_django.filters import FilterLookup

from facade import inputs, managers, models
from rekuest_core.inputs import types as ritypes


@strawberry_django.filter_type(models.Action)
class ImplementationActionFilter:
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
        if len(value) == 0:
            return queryset, Q()

        ids = managers.get_action_ids_by_port_demands(value, organization_id=info.context.request.organization.id)
        return queryset.filter(**{f"{prefix}id__in": ids}), Q()

    @filter_field
    def kind(self, info: Info, queryset, value: renums.ActionKind, prefix: str):
        return queryset.filter(**{f"{prefix}kind": value}), Q()

    @filter_field
    def protocols(self, info: Info, queryset, value: list[str], prefix: str):
        return queryset.filter(**{f"{prefix}protocols__name__in": value}), Q()


@strawberry_django.order_type(models.Implementation)
class ImplementationOrder:
    created_at: auto
    started_at: auto
    finished_at: auto
    status: auto

    @strawberry_django.order_field
    def active(self, value: strawberry_django.Ordering, prefix: str) -> list[str]:
        if not value:
            return []
        return [f"{prefix}agent__connected"]


@strawberry_django.filter_type(models.Implementation)
class ImplementationFilter:
    interface: Optional[FilterLookup[str]]
    action: ImplementationActionFilter | None
    agent: ImplementationAgentFilter | None

    @filter_field
    def active(self, info: Info, queryset, value: bool, prefix: str):
        now = timezone.now()
        if value:
            return queryset.filter(**{f"{prefix}agent__last_seen__gt": now - datetime.timedelta(minutes=5)}), Q()
        else:
            return queryset.filter(**{f"{prefix}agent__last_seen__lte": now - datetime.timedelta(minutes=5)}), Q()

    @filter_field
    def ids(self, info: Info, queryset, value: list[strawberry.ID], prefix: str):
        return queryset.filter(**{f"{prefix}id__in": value}), Q()

    @filter_field
    def action_hash(self, info: Info, queryset, value: rscalars.ActionHash, prefix: str):
        return queryset.filter(**{f"{prefix}action__hash": value}), Q()

    @filter_field
    def parameters(self, info: Info, queryset, value: list[ParamPair], prefix: str):
        for param in value:
            queryset = queryset.filter(**{f"{prefix}params__contains": {param.key: param.value}})
        return queryset, Q()

    @filter_field
    def resolvable_for(self, info: Info, queryset, value: strawberry.ID, prefix: str):
        dependency = models.Dependency.objects.get(id=value)
        return queryset.filter(**{f"{prefix}action__app__identifier": dependency.app_filter}), Q()

    @filter_field
    def search(self, info: Info, queryset, value: str, prefix: str):
        return queryset.filter(Q(**{f"{prefix}action__name__icontains": value}) | Q(**{f"{prefix}agent__name__icontains": value}) | Q(**{f"{prefix}interface__icontains": value})), Q()

    @filter_field
    def action_demand(self, info: Info, queryset, value: ritypes.ActionDemandInput, prefix: str):
        new_ids = managers.get_action_ids_by_action_demands(
            [value],
            organization_id=info.context.request.organization.id,
        )[0]
        return queryset.filter(**{f"{prefix}action__id__in": new_ids}), Q()
