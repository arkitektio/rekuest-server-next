"""Filters and orders for agents, hardware and implementation-agents."""

from __future__ import annotations

import strawberry
import strawberry_django
from django.db.models import Q
from strawberry import UNSET, auto
from strawberry.types import Info
from strawberry_django.fields.filter_order import filter_field

from facade import inputs, managers, models


@strawberry_django.filter_type(models.Agent, description="A way to filter agents")
class AgentFilter:
    @filter_field(description="Filter by scope")
    def scope(self, info: Info, queryset, value: ScopeFilter, prefix: str):
        q = Q()
        if value.public is not None:
            q &= Q(**{f"{prefix}is_public": value.public})
        if value.org is not None:
            q &= Q(**{f"{prefix}organization": info.context.request.organization})
        if value.shared is not None:
            raise NotImplementedError("Shared scope filtering not implemented")
        if value.me is not None:
            q &= Q(**{f"{prefix}creator": info.context.request.user})
        return queryset, q

    @filter_field(description="Filter by client ID of the app the agent is registered to")
    def client_id(self, info: Info, queryset, value: str, prefix: str):
        return queryset.filter(**{f"{prefix}registry__client__client_id": value}), Q()

    @filter_field(description="Filter by IDs of the agents")
    def ids(self, info: Info, queryset, value: list[strawberry.ID], prefix: str):
        return queryset.filter(**{f"{prefix}id__in": value}), Q()

    @filter_field(description="Filter by extensions of the agents")
    def extensions(self, info: Info, queryset, value: list[str], prefix: str):
        return queryset.filter(**{f"{prefix}extensions__contains": value}), Q()

    @filter_field(description="Filter by implementations of the agents")
    def has_implementations(self, info: Info, queryset, value: list[str], prefix: str):
        return queryset.filter(**{f"{prefix}implementations__action__hash__in": value}), Q()

    @filter_field(description="Filter by states of the agents")
    def has_states(self, info: Info, queryset, value: list[str], prefix: str):
        return queryset.filter(**{f"{prefix}states__state_schema__hash__in": value}), Q()

    @filter_field(description="Filter by pinned agents")
    def pinned(self, info: Info, queryset, value: bool, prefix: str):
        user = info.context.request.user
        if value:
            return queryset.filter(**{f"{prefix}pinned_by__id": user.id}), Q()
        else:
            return queryset.exclude(**{f"{prefix}pinned_by__id": user.id}), Q()

    @filter_field(description="Filter by name of the agents")
    def search(self, info: Info, queryset, value: str, prefix: str):
        if value == "":
            return queryset, Q()
        return queryset.filter(**{f"{prefix}name__icontains": value}), Q()

    @filter_field
    def dependency(self, info: Info, queryset, value: strawberry.ID, prefix: str):
        dep = models.Dependency.objects.get(id=value)
        if dep.app_filter is not UNSET and dep.app_filter is not None:
            return queryset.filter(**{f"{prefix}app__identifier": dep.app_filter}), Q()
        else:
            raise ValueError("Filtering by dependency currently only allowed when the dependency declared an app filter, sorry :( This is coming")

    @filter_field
    def blok_dependency(self, info: Info, queryset, value: strawberry.ID, prefix: str):
        dep = models.BlokDependency.objects.get(id=value)
        if dep.app_filter is not UNSET and dep.app_filter is not None:
            return queryset.filter(**{f"{prefix}app__identifier": dep.app_filter}), Q()
        else:
            raise ValueError("Filtering by blok_dependency currently only allowed when the blok_dependency declared an app filter, sorry :( This is coming")

    @filter_field
    def three_d_model(self, info: Info, queryset, value: strawberry.ID, prefix: str):
        dep = models.ThreeDModel.objects.get(id=value)
        if self.app_identifier is not UNSET and self.app_identifier is not None:
            return queryset.filter(**{f"{prefix}app__identifier": dep.app_filter}), Q()
        else:
            raise ValueError("Filtering by three_d_model currently only allowed when also filtering by app identifier")

    @filter_field
    def distinct(self, info: Info, queryset, value: bool, prefix: str):
        return queryset.distinct(), Q()

    @filter_field
    def action_demands(self, info: Info, queryset, value: list[inputs.ActionDemandInput], prefix: str):
        for ports_demand in value:
            new_ids = managers.get_action_ids_by_action_demand(
                action_demand=ports_demand,
                organization_id=info.context.request.organization.id,
            )

            if len(new_ids) == 0:
                raise ValueError(f"No actions found that match the given action demands {ports_demand}")

            queryset = queryset.filter(**{f"{prefix}implementations__action__id__in": new_ids})

        return queryset, Q()

    @filter_field
    def state_demands(self, info: Info, queryset, value: list[inputs.SchemaDemandInput], prefix: str):
        filtered_ids: set[str] = set()

        for state_demand in value:
            fitting_schema_ids = managers.get_state_ids_by_demands(
                state_demand.matches,
                model="facade_stateschema",
            )

            if len(fitting_schema_ids) == 0:
                return queryset.none(), Q()

            for new_id in fitting_schema_ids:
                if new_id not in filtered_ids:
                    filtered_ids.add(new_id)

        return queryset.filter(**{f"{prefix}states__state_schema__id__in": list(filtered_ids)}), Q()

    @filter_field(description="Filter by user ID")
    def user(self, info: Info, queryset, value: strawberry.ID, prefix: str):
        return queryset.filter(**{f"{prefix}user__sub": value}), Q()

    @filter_field(description="Filter using app identifier")
    def app_identifier(self, info: Info, queryset, value: strawberry.ID, prefix: str):
        return queryset.filter(**{f"{prefix}app__identifier": value}), Q()

    @filter_field(description="Filter based on version string")
    def version_number(self, info: Info, queryset, value: str, prefix: str):
        return queryset.filter(**{f"{prefix}release__version": value}), Q()

    @filter_field(description="Filter based on device")
    def device_id(self, info: Info, queryset, value: strawberry.ID, prefix: str):
        return queryset.filter(**{f"{prefix}device__device_id": value}), Q()


@strawberry_django.order_type(models.Agent)
class AgentOrder:
    last_seen: auto


@strawberry_django.filter_type(models.HardwareRecord)
class HardwareRecordFilter:
    @filter_field
    def ids(self, info: Info, queryset, value: list[strawberry.ID], prefix: str):
        return queryset.filter(**{f"{prefix}id__in": value}), Q()

    @filter_field
    def cpu_vendor_name(self, info: Info, queryset, value: str, prefix: str):
        return queryset.filter(**{f"{prefix}cpu_vendor_name__contains": value}), Q()


@strawberry_django.filter_type(models.Agent)
class ImplementationAgentFilter:
    @filter_field
    def client_id(self, info: Info, queryset, value: str, prefix: str):
        return queryset.filter(**{f"{prefix}registry__app__client_id": value}), Q()

    @filter_field
    def ids(self, info: Info, queryset, value: list[strawberry.ID], prefix: str):
        return queryset.filter(**{f"{prefix}id__in": value}), Q()

    @filter_field
    def extensions(self, info: Info, queryset, value: list[str], prefix: str):
        return queryset.filter(**{f"{prefix}extensions__contains": value}), Q()

    @filter_field
    def has_implementations(self, info: Info, queryset, value: list[str], prefix: str):
        return queryset.filter(**{f"{prefix}implementations__action__hash__in": value}), Q()

    @filter_field
    def has_states(self, info: Info, queryset, value: list[str], prefix: str):
        return queryset.filter(**{f"{prefix}states__state_schema__hash__in": value}), Q()
