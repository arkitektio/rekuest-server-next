"""Filters and orders for tasks and task events."""

from __future__ import annotations

import datetime

import strawberry
import strawberry_django
from django.db.models import Q
from strawberry import auto
from strawberry.types import Info
from strawberry_django.fields.filter_order import filter_field

from facade import enums, models


@strawberry_django.order_type(models.Task)
class TaskOrder:
    created_at: auto
    started_at: auto
    finished_at: auto
    status: auto


@strawberry_django.filter_type(models.Task)
class TaskFilter:
    @filter_field
    def ids(self, info: Info, queryset, value: list[strawberry.ID], prefix: str):
        return queryset.filter(**{f"{prefix}id__in": value}), Q()

    @filter_field
    def status(self, info: Info, queryset, value: list[enums.TaskStatus], prefix: str):
        return queryset.filter(**{f"{prefix}status__in": value}), Q()

    @filter_field
    def client_id(self, info: Info, queryset, value: strawberry.ID, prefix: str):
        return queryset.filter(**{f"{prefix}agent__client__client_id": value}), Q()

    @filter_field
    def state(self, info: Info, queryset, value: list[enums.TaskEventKind], prefix: str):
        return queryset.filter(**{f"{prefix}latest_event_kind__in": value}).distinct(), Q()

    @filter_field
    def implementation(self, info: Info, queryset, value: strawberry.ID, prefix: str):
        return queryset.filter(**{f"{prefix}implementation_id": value}), Q()

    @filter_field
    def acted_on(self, info: Info, queryset, value: list[str], prefix: str):
        return queryset.filter(**{f"{prefix}acted_on__overlap": value}), Q()

    @filter_field
    def created_before(self, info: Info, queryset, value: datetime.datetime, prefix: str):
        return queryset.filter(**{f"{prefix}created_at__lt": value}), Q()

    @filter_field
    def created_after(self, info: Info, queryset, value: datetime.datetime, prefix: str):
        return queryset.filter(**{f"{prefix}created_at__gt": value}), Q()

    @filter_field
    def agent(self, info: Info, queryset, value: strawberry.ID, prefix: str):
        return queryset.filter(**{f"{prefix}agent_id": value}), Q()


@strawberry_django.order_type(models.TaskEvent)
class TaskEventOrder:
    created_at: auto


@strawberry_django.filter_type(models.TaskEvent, description="A way to filter task events")
class TaskEventFilter:
    @filter_field
    def kind(self, info: Info, queryset, value: list[enums.TaskEventKind], prefix: str):
        return queryset.filter(**{f"{prefix}kind__in": value}), Q()
