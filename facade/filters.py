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
    client_id: str | None
    instance_id: str | None
    ids: list[strawberry.ID] | None
    extensions: list[str] | None
    has_templates: list[str] | None
    has_states: list[str] | None
    pinned: bool | None
    search: str | None
    distinct: bool | None
    
    def filter_search(self, queryset, info):
        if self.search is None:
            return queryset
        return queryset.filter(name__icontains=self.search)

    def filter_pinned(self, queryset, info):
        if self.pinned is None:
            return queryset
        if self.pinned:
            # Check if the user is in the pinned_by list
            return queryset.filter(pinned_by__id=info.context.request.user.id)
        else:
            return queryset.exclude(pinned_by__id=info.context.request.user.id)

    def filter_client_id(self, queryset, info):
        if self.client_id is None:
            return queryset
        return queryset.filter(registry__app__client_id=self.client_id)

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

    def filter_has_templates(self, queryset, info):
        if self.has_templates is None:
            return queryset
        return queryset.filter(templates__node__hash__in=self.has_templates)

    def filter_has_states(self, queryset, info):
        if self.has_states is None:
            return queryset
        return queryset.filter(states__state_schema__hash__in=self.has_states)
    

    def filter_distinct(self, queryset, info):
        if self.distinct is None:
            return queryset
        return queryset.distinct()


@strawberry_django.filter(models.Waiter)
class WaiterFilter:
    instance_id: scalars.InstanceID
    ids: list[strawberry.ID] | None

    def filter_ids(self, queryset, info):
        if self.ids is None:
            return queryset
        return queryset.filter(id__in=self.ids)


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
    last_seen: auto


@strawberry_django.order(models.Node)
class NodeOrder:
    defined_at: auto


@strawberry_django.order(models.Protocol)
class ProtocolOrder:
    name: auto


@strawberry_django.order(models.Shortcut)
class ShortcutOrder:
    name: auto
    
@strawberry_django.order(models.Toolbox)
class ToolboxOrder:
    name: auto

@strawberry_django.filter(models.Protocol)
class ProtocolFilter(SearchFilter):
    name: Optional[FilterLookup[str]]
    ids: list[strawberry.ID] | None

    def filter_ids(self, queryset, info):
        if self.ids is None:
            return queryset
        return queryset.filter(id__in=self.ids)


@strawberry_django.filter(models.Toolbox)
class ToolboxFilter(SearchFilter):
    name: Optional[FilterLookup[str]]
    ids: list[strawberry.ID] | None

    def filter_ids(self, queryset, info):
        if self.ids is None:
            return queryset
        return queryset.filter(id__in=self.ids)
    
    def filter_mine(self, queryset, info):
        if self.mine is None:
            return queryset
        return queryset.filter(user_id=info.context.user.id)


@strawberry_django.filter(models.Node)
class ShortcutNodeFilter(SearchFilter):
    name: str | None
    ids: list[strawberry.ID] | None
    demands: list[inputs.PortDemandInput] | None
    protocols: list[str] | None
    kind: Optional[renums.NodeKind] | None

    def filter_name(self, queryset, info):
        if self.name is None:
            return queryset
        return queryset.filter(node__name=self.name)

    def filter_demands(self, queryset, info):
        if self.demands is None:
            return queryset

        filtered_ids = None

        for ports_demand in self.demands:
            new_ids = managers.get_node_ids_by_demands(
                ports_demand.matches,
                type=ports_demand.kind,
                force_length=ports_demand.force_length,
                force_non_nullable_length=ports_demand.force_non_nullable_length,
                force_structure_length=ports_demand.force_structure_length,
            )

            if filtered_ids is None:
                filtered_ids = set(new_ids)
            else:
                filtered_ids = filtered_ids.intersection(new_ids)

        return queryset.filter(node__id__in=filtered_ids)

    def filter_kind(self, queryset, info):
        if self.kind is None:
            return queryset
        return queryset.filter(node__kind=self.kind)

    def filter_protocols(self, queryset, info):
        if self.protocols is None:
            return queryset
        return queryset.filter(node__protocols__name__in=self.protocols)

    def filter_ids(self, queryset, info):
        if self.ids is None:
            return queryset
        return queryset.filter(node__id__in=self.ids)

@strawberry_django.filter(models.Shortcut)
class ShortcutFilter(SearchFilter):
    ids: list[strawberry.ID] | None
    demands: list[inputs.PortDemandInput] | None
    toolbox: strawberry.ID | None
    
    def filter_toolbox(self, queryset, info):
        if self.toolbox is None:
            return queryset
        
        return queryset.filter(toolbox_id=self.toolbox)
    
    def filter_demands(self, queryset, info):
        if self.demands is None:
            return queryset

        filtered_ids = None

        for ports_demand in self.demands:
            new_ids = managers.get_node_ids_by_demands(
                ports_demand.matches,
                type=ports_demand.kind,
                force_length=ports_demand.force_length,
                force_non_nullable_length=ports_demand.force_non_nullable_length,
                force_structure_length=ports_demand.force_structure_length,
                model="facade_shortcut",
            )

            if filtered_ids is None:
                filtered_ids = set(new_ids)
            else:
                filtered_ids = filtered_ids.intersection(new_ids)

        return queryset.filter(id__in=filtered_ids)

    def filter_ids(self, queryset, info):
        if self.ids is None:
            return queryset
        return queryset.filter(id__in=self.ids)
    
    def filter_mine(self, queryset, info):
        if self.mine is None:
            return queryset
        
        return queryset.filter(user_id=info.context.user.id)

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
                force_structure_length=ports_demand.force_structure_length,
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


@strawberry_django.filter(models.Agent)
class TemplateAgentFilter:
    client_id: str | None
    instance_id: str | None
    ids: list[strawberry.ID] | None
    extensions: list[str] | None
    has_templates: list[str] | None
    has_states: list[str] | None

    def filter_client_id(self, queryset, info):
        if self.client_id is None:
            return queryset
        return queryset.filter(agent__registry__app__client_id=self.client_id)

    def filter_ids(self, queryset, info):
        if self.ids is None:
            return queryset
        return queryset.filter(agent__id__in=self.ids)

    def filter_instance_id(self, queryset, info):
        if self.instance_id is None:
            return queryset
        return queryset.filter(agent__instance_id=self.instance_id)

    def filter_extensions(self, queryset, info):
        if self.extensions is None:
            return queryset
        return queryset.filter(agent__extensions__contains=self.extensions)

    def filter_has_states(self, queryset, info):
        if self.has_states is None:
            return queryset
        return queryset.filter(agent__states__state_schema__hash__in=self.has_states)


@strawberry_django.filter(models.Node)
class TemplateNodeFilter(SearchFilter):
    name: str | None
    ids: list[strawberry.ID] | None
    demands: list[inputs.PortDemandInput] | None
    protocols: list[str] | None
    kind: Optional[renums.NodeKind] | None

    def filter_name(self, queryset, info):
        if self.name is None:
            return queryset
        return queryset.filter(node__name=self.name)

    def filter_demands(self, queryset, info):
        if self.demands is None:
            return queryset

        filtered_ids = None

        for ports_demand in self.demands:
            new_ids = managers.get_node_ids_by_demands(
                ports_demand.matches,
                type=ports_demand.kind,
                force_length=ports_demand.force_length,
                force_non_nullable_length=ports_demand.force_non_nullable_length,
                force_structure_length=ports_demand.force_structure_length,
            )

            if filtered_ids is None:
                filtered_ids = set(new_ids)
            else:
                filtered_ids = filtered_ids.intersection(new_ids)

        return queryset.filter(node__id__in=filtered_ids)

    def filter_kind(self, queryset, info):
        if self.kind is None:
            return queryset
        return queryset.filter(node__kind=self.kind)

    def filter_protocols(self, queryset, info):
        if self.protocols is None:
            return queryset
        return queryset.filter(node__protocols__name__in=self.protocols)

    def filter_ids(self, queryset, info):
        if self.ids is None:
            return queryset
        return queryset.filter(node__id__in=self.ids)


@strawberry.input
class ParamPair:
    key: str
    value: str


@strawberry_django.filter(models.Template)
class TemplateFilter:
    interface: Optional[FilterLookup[str]]
    ids: list[strawberry.ID] | None
    node_hash: rscalars.NodeHash | None
    node: TemplateNodeFilter | None
    extension: str | None
    agent: TemplateAgentFilter | None
    parameters: list[ParamPair] | None

    def filter_ids(self, queryset, info):
        if self.ids is None:
            return queryset
        return queryset.filter(id__in=self.ids)

    def filter_extension(self, queryset, info):
        if self.extension is None:
            return queryset
        return queryset.filter(extension=self.extension)

    def filter_node_hash(self, queryset, info):
        if self.node_hash is None:
            return queryset
        return queryset.filter(node__hash=self.node_hash)

    def filter_parameters(self, queryset, info):
        if self.parameters is None:
            return queryset
        for param in self.parameters:
            queryset = queryset.filter(params__contains={param.key: param.value})
        return queryset
