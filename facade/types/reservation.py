"""The Reservation GraphQL type."""

from __future__ import annotations

import datetime
from typing import Optional

import strawberry
import strawberry_django

from facade import enums, filters, models


@strawberry_django.type(models.Reservation, filters=filters.ReservationFilter, pagination=True, description="Reservation for planned assignment of implementations.")
class Reservation:
    id: strawberry.ID = strawberry_django.field(description="ID of the reservation.")
    name: str = strawberry_django.field(description="Name of the reservation.")
    waiter: "Waiter" = strawberry_django.field(description="Waiter associated with the reservation.")
    title: str | None = strawberry_django.field(description="Optional title.")
    action: "Action" = strawberry_django.field(description="Action this reservation is for.")
    updated_at: datetime.datetime = strawberry_django.field(description="Last update timestamp.")
    reference: str = strawberry_django.field(description="Reference string for identification.")
    implementations: list["Implementation"] = strawberry_django.field(description="Available implementations for the reservation.")
    causing_dependency: Dependency | None = strawberry_django.field(description="Dependency that triggered the reservation.")
    strategy: enums.ReservationStrategy = strawberry_django.field(description="Reservation strategy applied.")
    viable: bool = strawberry_django.field(description="Is the reservation currently viable.")
    happy: bool = strawberry_django.field(description="Did the reservation succeed.")
    implementation: Optional["Implementation"] = strawberry_django.field(description="Chosen implementation.")
