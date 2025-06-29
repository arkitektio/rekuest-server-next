from typing import Optional

import strawberry
import strawberry_django
from authentikate.models import Client, User
from authentikate.vars import get_user
from facade import enums, inputs, managers, models, scalars
from rekuest_core import enums as renums
from rekuest_core import scalars as rscalars
from strawberry import auto
from strawberry_django.filters import FilterLookup


@strawberry.input(description="A way to filter users")
class SearchFilter:
    search: Optional[str] | None

    def filter_search(self, queryset, info):
        if self.search is None:
            return queryset
        return queryset.filter(name__icontains=self.search)


@strawberry_django.filter(models.TestCase, description="A way to filter test cases")
class TestCaseFilter:
    name: Optional[FilterLookup[str]]
    ids: list[strawberry.ID] | None

    def filter_ids(self, queryset, info):
        if self.ids is None:
            return queryset
        return queryset.filter(id__in=self.ids)


@strawberry_django.filter(models.Agent, description="A way to filter agents")
class AgentFilter:
    client_id: str | None = strawberry.field(
        default=None,
        description="Filter by client ID of the app the agent is registered to",
    )
    instance_id: str | None = strawberry.field(
        default=None,
        description="Filter by instance ID of the agent",
    )
    ids: list[strawberry.ID] | None = strawberry.field(
        default=None,
        description="Filter by IDs of the agents",
    )
    extensions: list[str] | None = strawberry.field(
        default=None,
        description="Filter by extensions of the agents",
    )
    has_implementations: list[str] | None = strawberry.field(
        default=None,
        description="Filter by implementations of the agents",
    )
    has_states: list[str] | None = strawberry.field(
        default=None,
        description="Filter by states of the agents",
    )
    pinned: bool | None = strawberry.field(
        default=None,
        description="Filter by pinned agents",
    )
    search: str | None = strawberry.field(
        default=None,
        description="Filter by name of the agents",
    )
    distinct: bool | None
    action_demands: list[inputs.ActionDemandInput] | None
    state_demands: list[inputs.SchemaDemandInput] | None

    def filter_search(self, queryset, info):
        if self.search is None:
            return queryset
        return queryset.filter(name__icontains=self.search)

    def filter_pinned(self, queryset, info):
        if self.pinned is None:
            return queryset

        user = info.context.request.user
        if self.pinned:
            # Check if the user is in the pinned_by list
            return queryset.filter(pinned_by__id=user.id)
        else:
            return queryset.exclude(pinned_by__id=user.id)

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

    def filter_has_implementations(self, queryset, info):
        if self.has_implementations is None:
            return queryset
        return queryset.filter(implementations__action__hash__in=self.has_implementations)

    def filter_has_states(self, queryset, info):
        if self.has_states is None:
            return queryset
        return queryset.filter(states__state_schema__hash__in=self.has_states)

    def filter_distinct(self, queryset, info):
        if self.distinct is None:
            return queryset
        return queryset.distinct()

    def filter_action_demands(self, queryset, info):
        if self.action_demands is None:
            return queryset

        filtered_ids: set[str] = set()

        for ports_demand in self.action_demands:
            new_ids = managers.get_action_ids_by_action_demand(
                action_demand=ports_demand,
            )

            if len(new_ids) == 0:
                # There are no actions that match the demand
                raise ValueError(
                    f"No actions found that match the given action demands {ports_demand}"
                )

            for new_id in new_ids:
                if new_id not in filtered_ids:
                    filtered_ids.add(new_id)

        return queryset.filter(implementations__action__id__in=filtered_ids)

    def filter_state_demands(self, queryset, info):
        if self.state_demands is None:
            return queryset

        filtered_ids = None

        filtered_ids: set[str] = set()

        for state_demand in self.state_demands:
            fitting_schema_ids = managers.get_state_ids_by_demands(
                state_demand.matches,
                model="facade_stateschema",
            )

            if len(fitting_schema_ids) == 0:
                return queryset.none()

            for new_id in fitting_schema_ids:
                if new_id not in filtered_ids:
                    filtered_ids.add(new_id)

        return queryset.filter(states__state_schema__id__in=list(filtered_ids))


@strawberry_django.filter(models.Waiter, description="A way to filter waiters")
class WaiterFilter:
    instance_id: scalars.InstanceID
    ids: list[strawberry.ID] | None

    def filter_ids(self, queryset, info):
        if self.ids is None:
            return queryset
        return queryset.filter(id__in=self.ids)


@strawberry_django.filter(models.FilesystemShelve, description="A way to filter shelved items")
class FilesystemShelveFilter:
    ids: list[strawberry.ID] | None

    def filter_ids(self, queryset, info):
        if self.ids is None:
            return queryset
        return queryset.filter(id__in=self.ids)


@strawberry_django.filter(models.MemoryShelve, description="A way to filter shelved items")
class MemoryShelveFilter:
    agent: strawberry.ID | None
    ids: list[strawberry.ID] | None

    def filter_ids(self, queryset, info):
        if self.ids is None:
            return queryset
        return queryset.filter(id__in=self.ids)


@strawberry_django.filter(models.FileDrawer, description="A way to filter shelved items")
class FileDrawerFilter:
    shelve: strawberry.ID | None
    agent: strawberry.ID | None
    identifier: str | None
    ids: list[strawberry.ID] | None

    def filter_ids(self, queryset, info):
        if self.ids is None:
            return queryset
        return queryset.filter(id__in=self.ids)


@strawberry_django.filter(models.MemoryDrawer, description="A way to filter shelved items")
class MemoryDrawerFilter:
    shelve: strawberry.ID | None
    agent: strawberry.ID | None
    implementation: strawberry.ID | None
    identifier: str | None
    ids: list[strawberry.ID] | None
    search: str | None

    def filter_search(self, queryset, info):
        if self.search is None:
            return queryset
        return queryset.filter(label__icontains=self.search)

    def filter_ids(self, queryset, info):
        if self.ids is None:
            return queryset
        return queryset.filter(id__in=self.ids)

    def filter_implementation(self, queryset, info):
        if self.implementation is None:
            return queryset
        return queryset.filter(shelve__agent__implementations=self.implementation)

    def filter_identifier(self, queryset, info):
        if self.identifier is None:
            return queryset
        return queryset.filter(identifier=self.identifier)


@strawberry_django.filter(models.Reservation, description="A way to filter reservations")
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


@strawberry_django.filter(models.AssignationEvent, description="A way to filter assignation events")
class AssignationEventFilter:
    kind: list[enums.AssignationEventKind] | None

    def filter_kind(self, queryset, info):
        if self.kind is None:
            return queryset
        return queryset.filter(kind__in=self.kind)


@strawberry_django.filter(models.TestResult, description="A way to filter test results")
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


@strawberry_django.filter(User)
class UserFilter:
    ids: list[strawberry.ID] | None
    name: Optional[FilterLookup[str]]

    def filter_ids(self, queryset, info):
        if self.ids is None:
            return queryset
        return queryset.filter(id__in=self.ids)

    def filter_name(self, queryset, info):
        if self.name is None:
            return queryset
        return queryset.filter(name__icontains=self.name)


@strawberry_django.order(User)
class UserOrder:
    name: auto
    email: auto
    date_joined: auto
    last_login: auto


@strawberry_django.order(Client, description="A way to order apps")
class ClientOrder:
    defined_at: auto


@strawberry_django.filter(Client, description="A way to filter apps")
class ClientFilter:
    interface: Optional[FilterLookup[str]]
    ids: list[strawberry.ID] | None
    has_implementations_for: list[rscalars.ActionHash] | None
    mine: bool | None

    def filter_ids(self, queryset, info):
        if self.ids is None:
            return queryset
        return queryset.filter(id__in=self.ids)

    def filter_has_implementations_for(self, queryset, info):
        if self.has_implementations_for is None:
            return queryset
        return queryset.filter(registry__agents__implementations__action__hash__in=self.has_implementations_for).distinct()

    def filter_mine(self, queryset, info):
        if self.mine is None:
            return queryset
        return queryset.filter(user_id=info.context.user.id)


@strawberry_django.order(models.Agent)
class AgentOrder:
    last_seen: auto


@strawberry_django.order(models.Action)
class ActionOrder:
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


@strawberry_django.order(models.MemoryShelve)
class MemoryShelveOrder:
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


@strawberry_django.filter(models.Action)
class ShortcutActionFilter(SearchFilter):
    name: str | None
    ids: list[strawberry.ID] | None
    demands: list[inputs.PortDemandInput] | None
    protocols: list[str] | None
    kind: Optional[renums.ActionKind] | None

    def filter_name(self, queryset, info):
        if self.name is None:
            return queryset
        return queryset.filter(action__name=self.name)

    def filter_demands(self, queryset, info):
        if self.demands is None:
            return queryset

        filtered_ids = None

        for ports_demand in self.demands:
            new_ids = managers.get_action_ids_by_demands(
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

        return queryset.filter(action__id__in=filtered_ids)

    def filter_kind(self, queryset, info):
        if self.kind is None:
            return queryset
        return queryset.filter(action__kind=self.kind)

    def filter_protocols(self, queryset, info):
        if self.protocols is None:
            return queryset
        return queryset.filter(action__protocols__name__in=self.protocols)

    def filter_ids(self, queryset, info):
        if self.ids is None:
            return queryset
        return queryset.filter(action__id__in=self.ids)


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
            new_ids = managers.get_action_ids_by_demands(
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


@strawberry_django.filter(models.Action)
class ActionFilter(SearchFilter):
    name: Optional[FilterLookup[str]]
    ids: list[strawberry.ID] | None
    demands: list[inputs.PortDemandInput] | None
    protocols: list[str] | None
    kind: Optional[renums.ActionKind] | None

    def filter_demands(self, queryset, info):
        if self.demands is None:
            return queryset

        for ports_demand in self.demands:
            queryset = managers.filter_actions_by_demands(
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
class ImplementationAgentFilter:
    client_id: str | None
    instance_id: str | None
    ids: list[strawberry.ID] | None
    extensions: list[str] | None
    has_implementations: list[str] | None
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


@strawberry_django.filter(models.Action)
class ImplementationActionFilter(SearchFilter):
    name: str | None
    ids: list[strawberry.ID] | None
    demands: list[inputs.PortDemandInput] | None
    protocols: list[str] | None
    kind: Optional[renums.ActionKind] | None

    def filter_name(self, queryset, info):
        if self.name is None:
            return queryset
        return queryset.filter(action__name=self.name)

    def filter_demands(self, queryset, info):
        if self.demands is None:
            return queryset

        filtered_ids = None

        for ports_demand in self.demands:
            new_ids = managers.get_action_ids_by_demands(
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

        return queryset.filter(action__id__in=filtered_ids)

    def filter_kind(self, queryset, info):
        if self.kind is None:
            return queryset
        return queryset.filter(action__kind=self.kind)

    def filter_protocols(self, queryset, info):
        if self.protocols is None:
            return queryset
        return queryset.filter(action__protocols__name__in=self.protocols)

    def filter_ids(self, queryset, info):
        if self.ids is None:
            return queryset
        return queryset.filter(action__id__in=self.ids)


@strawberry.input
class ParamPair:
    key: str
    value: str


@strawberry_django.filter(models.Implementation)
class ImplementationFilter:
    interface: Optional[FilterLookup[str]]
    ids: list[strawberry.ID] | None
    action_hash: rscalars.ActionHash | None
    action: ImplementationActionFilter | None
    extension: str | None
    agent: ImplementationAgentFilter | None
    parameters: list[ParamPair] | None

    def filter_ids(self, queryset, info):
        if self.ids is None:
            return queryset
        return queryset.filter(id__in=self.ids)

    def filter_extension(self, queryset, info):
        if self.extension is None:
            return queryset
        return queryset.filter(extension=self.extension)

    def filter_action_hash(self, queryset, info):
        if self.action_hash is None:
            return queryset
        return queryset.filter(action__hash=self.action_hash)

    def filter_parameters(self, queryset, info):
        if self.parameters is None:
            return queryset
        for param in self.parameters:
            queryset = queryset.filter(params__contains={param.key: param.value})
        return queryset
