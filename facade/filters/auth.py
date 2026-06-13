"""Filters and orders for authentication/organization models."""

from __future__ import annotations

from typing import Optional

import strawberry
import strawberry_django
from authentikate.models import Client, Organization, User
from django.db.models import Q
from rekuest_core import scalars as rscalars
from strawberry import auto
from strawberry.types import Info
from strawberry_django.fields.filter_order import filter_field
from strawberry_django.filters import FilterLookup


@strawberry_django.filter_type(User)
class UserFilter:
    name: Optional[FilterLookup[str]]

    @filter_field
    def ids(self, info: Info, queryset, value: list[strawberry.ID], prefix: str):
        return queryset.filter(**{f"{prefix}id__in": value}), Q()


@strawberry_django.order_type(User)
class UserOrder:
    name: auto
    email: auto
    date_joined: auto
    last_login: auto


@strawberry_django.order_type(Organization, description="A way to order registries")
class OrganizationOrder:
    slug: auto


@strawberry_django.filter_type(Organization, description="A way to filter organizations")
class OrganizationFilter:
    slug: Optional[FilterLookup[str]]

    @filter_field
    def ids(self, info: Info, queryset, value: list[strawberry.ID], prefix: str):
        return queryset.filter(**{f"{prefix}id__in": value}), Q()


@strawberry_django.order_type(Client, description="A way to order apps")
class ClientOrder:
    defined_at: auto


@strawberry_django.filter_type(Client, description="A way to filter apps")
class ClientFilter:
    interface: Optional[FilterLookup[str]]

    @filter_field
    def ids(self, info: Info, queryset, value: list[strawberry.ID], prefix: str):
        return queryset.filter(**{f"{prefix}id__in": value}), Q()

    @filter_field
    def has_implementations_for(self, info: Info, queryset, value: list[rscalars.ActionHash], prefix: str):
        return queryset.filter(**{f"{prefix}registry__agents__implementations__action__hash__in": value}).distinct(), Q()

    @filter_field
    def mine(self, info: Info, queryset, value: bool, prefix: str):
        return queryset.filter(**{f"{prefix}user_id": info.context.user.id}), Q()
