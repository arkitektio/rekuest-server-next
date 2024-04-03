import strawberry
from facade import models, scalars, enums, inputs, managers
from strawberry import auto
from typing import Optional
from strawberry_django.filters import FilterLookup
import strawberry_django



@strawberry.input
class SearchFilter:
    search: Optional[str] | None

    def filter_search(self, queryset, info):
        if self.search is None:
            return queryset
        return queryset.filter(name__icontains=self.search)


@strawberry_django.filter(models.TestCase)
class TestCaseFilter:
    name: Optional[FilterLookup[str]]
    ids: list[strawberry.ID] | None

    def filter_ids(self, queryset, info):
        if self.ids is None:
            return queryset
        return queryset.filter(id__in=self.ids)


@strawberry_django.filter(models.Agent)
class AgentFilter:
    instance_id: str
    ids: list[strawberry.ID] | None

    def filter_ids(self, queryset, info):
        if self.ids is None:
            return queryset
        return queryset.filter(id__in=self.ids)


@strawberry_django.filter(models.Waiter)
class WaiterFilter:
    instance_id: scalars.InstanceID
    ids: list[strawberry.ID] | None

    def filter_ids(self, queryset, info):
        if self.ids is None:
            return queryset
        return queryset.filter(id__in=self.ids)


@strawberry_django.filter(models.Provision)
class ProvisionFilter:
    agent: AgentFilter | None
    ids: list[strawberry.ID] | None
    status: list[enums.ProvisionStatus] | None

    def filter_ids(self, queryset, info):
        if self.ids is None:
            return queryset
        return queryset.filter(id__in=self.ids)

    def filter_status(self, queryset, info):
        if self.status is None:
            return queryset
        return queryset.filter(status__in=self.status)


@strawberry_django.filter(models.ProvisionEvent)
class ProvisionEventFilter:
    kind: list[enums.ProvisionEventKind] | None

    def filter_kind(self, queryset, info):
        if self.kind is None:
            return queryset
        return queryset.filter(kind__in=self.kind)


@strawberry_django.filter(models.Reservation)
class ReservationFilter:
    waiter: WaiterFilter | None
    ids: list[strawberry.ID] | None
    status: list[enums.ReservationStatus] | None

    def filter_ids(self, queryset, info):
        if self.ids is None:
            return queryset
        return queryset.filter(id__in=self.ids)

    def filter_status(self, queryset, info):
        if self.status is None:
            return queryset
        return queryset.filter(status__in=self.status)


@strawberry_django.filter(models.ReservationEvent)
class ReservationEventFilter:
    kind: list[enums.ReservationEventKind] | None

    def filter_kind(self, queryset, info):
        if self.kind is None:
            return queryset
        return queryset.filter(kind__in=self.kind)


@strawberry_django.filter(models.Assignation)
class AssignationFilter:
    reservation: ReservationFilter | None
    ids: list[strawberry.ID] | None
    status: list[enums.AssignationStatus] | None

    def filter_ids(self, queryset, info):
        if self.ids is None:
            return queryset
        return queryset.filter(id__in=self.ids)

    def filter_status(self, queryset, info):
        if self.status is None:
            return queryset
        return queryset.filter(status__in=self.status)


@strawberry_django.filter(models.AssignationEvent)
class AssignationEventFilter:
    kind: list[enums.AssignationEventKind] | None

    def filter_kind(self, queryset, info):
        if self.kind is None:
            return queryset
        return queryset.filter(kind__in=self.kind)


@strawberry_django.filter(models.TestResult)
class TestResultFilter:
    name: Optional[FilterLookup[str]]
    ids: list[strawberry.ID] | None

    def filter_ids(self, queryset, info):
        if self.ids is None:
            return queryset
        return queryset.filter(id__in=self.ids)


@strawberry_django.filter(models.Template)
class TemplateFilter:
    interface: Optional[FilterLookup[str]]
    ids: list[strawberry.ID] | None

    def filter_ids(self, queryset, info):
        if self.ids is None:
            return queryset
        return queryset.filter(id__in=self.ids)


@strawberry_django.order(models.Node)
class NodeOrder:
    defined_at: auto


@strawberry_django.order(models.Protocol)
class ProtocolOrder:
    name: auto

@strawberry_django.filter(models.Protocol)
class ProtocolFilter(SearchFilter):
    name: Optional[FilterLookup[str]]
    ids: list[strawberry.ID] | None

    def filter_ids(self, queryset, info):
        if self.ids is None:
            return queryset
        return queryset.filter(id__in=self.ids)


@strawberry_django.filter(models.Node)
class NodeFilter(SearchFilter):
    name: Optional[FilterLookup[str]]
    ids: list[strawberry.ID] | None
    demands: list[inputs.PortDemandInput] | None
    protocols: list[strawberry.ID] | None

    def filter_demands(self, queryset, info):
        if self.demands is None:
            return queryset
        
        for ports_demand in self.demands:
            queryset = managers.filter_nodes_by_demands(queryset, ports_demand.matches, type=ports_demand.kind, force_length=ports_demand.force_length, force_non_nullable_length=ports_demand.force_non_nullable_length)
        
        
        return queryset
    
    def filter_protocols(self, queryset, info):
        if self.protocols is None:
            return queryset
        return queryset.filter(protocols__id__in=self.protocols)


    def filter_ids(self, queryset, info):
        if self.ids is None:
            return queryset
        return queryset.filter(id__in=self.ids)
