"""Filters for reservations."""

from __future__ import annotations

import strawberry
import strawberry_django
from django.db.models import Q
from strawberry.types import Info
from strawberry_django.fields.filter_order import filter_field

from facade import enums, models


@strawberry_django.filter_type(models.Reservation, description="A way to filter reservations")
class ReservationFilter:
    @filter_field
    def ids(self, info: Info, queryset, value: list[strawberry.ID], prefix: str):
        return queryset.filter(**{f"{prefix}id__in": value}), Q()

    @filter_field
    def status(self, info: Info, queryset, value: list[enums.ReservationStatus], prefix: str):
        return queryset.filter(**{f"{prefix}status__in": value}), Q()
