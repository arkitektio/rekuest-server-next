from typing import Optional

import strawberry
import strawberry_django
from authentikate.models import App, User
from facade import enums, inputs, managers, models, scalars
from rekuest_core import enums as renums
from rekuest_core import scalars as rscalars
from strawberry import auto
from strawberry_django.filters import FilterLookup


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
    instance_id: str | None
    ids: list[strawberry.ID] | None
    extensions: list[str] | None

    def filter_ids(self, queryset, info):
        if self.ids is None:
            return queryset
        return queryset.filter(id__in=self.ids)
    
    def filter_instance_id(self, queryset, info):
        if self.instance_id is None:
            return queryset
        return queryset.filter(instance_id=self.instance_id)
    
    def filter_extensions(self, queryset, info):
        if self.extensions is None:
            return queryset
        return queryset.filter(extensions__contains=self.extensions)


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
    instance_id: scalars.InstanceID | None

    def filter_ids(self, queryset, info):
        if self.ids is None:
            return queryset
        return queryset.filter(id__in=self.ids)

    def filter_status(self, queryset, info):
        if self.status is None:
            return queryset
        return queryset.filter(status__in=self.status)

    def filter_instance_id(self, queryset, info):
        if self.instance_id is None:
            return queryset
        return queryset.filter(reservation__waiter__instance_id=self.instance_id)


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




@strawberry_django.filter(models.Dependency)
class DependencyFilter:
    ids: list[strawberry.ID] | None

    def filter_ids(self, queryset, info):
        if self.ids is None:
            return queryset
        return queryset.filter(id__in=self.ids)


@strawberry_django.order(App)
class AppOrder:
    defined_at: auto


@strawberry_django.filter(App)
class AppFilter:
    interface: Optional[FilterLookup[str]]
    ids: list[strawberry.ID] | None
    has_templates_for: list[rscalars.NodeHash] | None
    mine: bool | None

    def filter_ids(self, queryset, info):
        if self.ids is None:
            return queryset
        return queryset.filter(id__in=self.ids)

    def filter_has_templates_for(self, queryset, info):
        if self.has_templates_for is None:
            return queryset
        return queryset.filter(
            registry__agents__templates__node__hash__in=self.has_templates_for
        ).distinct()

    def filter_mine(self, queryset, info):
        if self.mine is None:
            return queryset
        return queryset.filter(user_id=info.context.user.id)


@strawberry_django.order(models.Agent)
class AgentOrder:
    installed_at: auto


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


@strawberry_django.filter(models.HardwareRecord)
class HardwareRecordFilter:
    ids: list[strawberry.ID] | None
    cpu_vendor_name: str | None

    def filter_ids(self, queryset, info):
        if self.ids is None:
            return queryset
        return queryset.filter(id__in=self.ids)

    def filter_cpu_vendor_name(self, queryset, info):
        if self.cpu_vendor_name is None:
            return queryset

        return queryset.filter(cpu_vendor_name__contains=self.cpu_vendor_name)


@strawberry_django.filter(models.Node)
class NodeFilter(SearchFilter):
    name: Optional[FilterLookup[str]]
    ids: list[strawberry.ID] | None
    demands: list[inputs.PortDemandInput] | None
    protocols: list[str] | None
    kind: Optional[renums.NodeKind] | None

    def filter_demands(self, queryset, info):
        if self.demands is None:
            return queryset

        for ports_demand in self.demands:
            queryset = managers.filter_nodes_by_demands(
                queryset,
                ports_demand.matches,
                type=ports_demand.kind,
                force_length=ports_demand.force_length,
                force_non_nullable_length=ports_demand.force_non_nullable_length,
            )

        return queryset

    def filter_kind(self, queryset, info):
        if self.kind is None:
            return queryset
        return queryset.filter(kind=self.kind)

    def filter_protocols(self, queryset, info):
        if self.protocols is None:
            return queryset
        return queryset.filter(protocols__name__in=self.protocols)

    def filter_ids(self, queryset, info):
        if self.ids is None:
            return queryset
        return queryset.filter(id__in=self.ids)

@strawberry_django.filter(models.Template)
class TemplateFilter:
    interface: Optional[FilterLookup[str]]
    ids: list[strawberry.ID] | None
    node: NodeFilter | None
    extension: str | None

    def filter_ids(self, queryset, info):
        if self.ids is None:
            return queryset
        return queryset.filter(id__in=self.ids)
    
    def filter_extension(self, queryset, info):
        if self.extension is None:
            return queryset
        return queryset.filter(extension=self.extension)
    
