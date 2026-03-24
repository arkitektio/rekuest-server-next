import datetime
from typing import Optional

import strawberry
import strawberry_django
from strawberry import UNSET
from authentikate.models import Client, User, Organization
from authentikate.vars import get_user
from facade import enums, inputs, managers, models, scalars
from rekuest_core import enums as renums
from rekuest_core.inputs import models as rimodels
from rekuest_core import scalars as rscalars
from strawberry import auto
from strawberry_django.filters import FilterLookup
from strawberry_django.fields.filter_order import filter_field
from django.db.models import Max, Q


@strawberry.input(description="A way to filter by scope")
class ScopeFilter:
    public: bool | None = None
    org: bool | None = None
    shared: bool | None = None
    me: bool | None = None


@strawberry_django.filter_type(models.TestCase, description="A way to filter test cases")
class TestCaseFilter:
    name: Optional[FilterLookup[str]]

    @filter_field
    def ids(self, info, queryset, value: list[strawberry.ID], prefix: str):
        return queryset.filter(**{f"{prefix}id__in": value}), Q()


@strawberry_django.filter_type(models.Resolution, description="A way to filter test cases")
class ResolutionFilter:
    name: Optional[FilterLookup[str]]

    @filter_field
    def ids(self, info, queryset, value: list[strawberry.ID], prefix: str):
        return queryset.filter(**{f"{prefix}id__in": value}), Q()


@strawberry_django.filter_type(models.ResolvedDependency, description="A way to filter resolved dependencies")
class ResolvedDependencyFilter:

    @filter_field
    def ids(self, info, queryset, value: list[strawberry.ID], prefix: str):
        return queryset.filter(**{f"{prefix}id__in": value}), Q()


@strawberry_django.filter_type(models.Agent, description="A way to filter agents")
class AgentFilter:

    @filter_field(description="Filter by scope")
    def scope(self, info, queryset, value: ScopeFilter, prefix: str):
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
    def client_id(self, info, queryset, value: str, prefix: str):
        return queryset.filter(**{f"{prefix}registry__client__client_id": value}), Q()

    @filter_field(description="Filter by instance ID of the agent")
    def instance_id(self, info, queryset, value: str, prefix: str):
        return queryset.filter(**{f"{prefix}instance_id": value}), Q()

    @filter_field(description="Filter by IDs of the agents")
    def ids(self, info, queryset, value: list[strawberry.ID], prefix: str):
        return queryset.filter(**{f"{prefix}id__in": value}), Q()

    @filter_field(description="Filter by extensions of the agents")
    def extensions(self, info, queryset, value: list[str], prefix: str):
        return queryset.filter(**{f"{prefix}extensions__contains": value}), Q()

    @filter_field(description="Filter by implementations of the agents")
    def has_implementations(self, info, queryset, value: list[str], prefix: str):
        return queryset.filter(**{f"{prefix}implementations__action__hash__in": value}), Q()

    @filter_field(description="Filter by states of the agents")
    def has_states(self, info, queryset, value: list[str], prefix: str):
        return queryset.filter(**{f"{prefix}states__state_schema__hash__in": value}), Q()

    @filter_field(description="Filter by pinned agents")
    def pinned(self, info, queryset, value: bool, prefix: str):
        user = info.context.request.user
        if value:
            return queryset.filter(**{f"{prefix}pinned_by__id": user.id}), Q()
        else:
            return queryset.exclude(**{f"{prefix}pinned_by__id": user.id}), Q()

    @filter_field(description="Filter by name of the agents")
    def search(self, info, queryset, value: str, prefix: str):
        if value == "":
            return queryset, Q()
        return queryset.filter(**{f"{prefix}name__icontains": value}), Q()

    @filter_field
    def dependency(self, info, queryset, value: strawberry.ID, prefix: str):
        dep = models.Dependency.objects.get(id=value)
        if self.app_identifier is not UNSET and self.app_identifier is not None:
            return queryset.filter(**{f"{prefix}app__identifier": dep.app_filter}), Q()
        else:
            raise ValueError("Filtering by dependency currently only allowed when also filtering by app identifier")

    @filter_field
    def distinct(self, info, queryset, value: bool, prefix: str):
        return queryset.distinct(), Q()

    @filter_field
    def action_demands(self, info, queryset, value: list[inputs.ActionDemandInput], prefix: str):
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
    def state_demands(self, info, queryset, value: list[inputs.SchemaDemandInput], prefix: str):
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
    def user(self, info, queryset, value: strawberry.ID, prefix: str):
        return queryset.filter(**{f"{prefix}user__sub": value}), Q()

    @filter_field(description="Filter using app identifier")
    def app_identifier(self, info, queryset, value: strawberry.ID, prefix: str):
        return queryset.filter(**{f"{prefix}app__identifier": value}), Q()

    @filter_field(description="Filter based on version string")
    def version_number(self, info, queryset, value: str, prefix: str):
        return queryset.filter(**{f"{prefix}release__version": value}), Q()

    @filter_field(description="Filter based on device")
    def device_id(self, info, queryset, value: strawberry.ID, prefix: str):
        return queryset.filter(**{f"{prefix}device__device_id": value}), Q()


@strawberry_django.filter_type(models.Waiter, description="A way to filter waiters")
class WaiterFilter:
    instance_id: scalars.InstanceId

    @filter_field
    def ids(self, info, queryset, value: list[strawberry.ID], prefix: str):
        return queryset.filter(**{f"{prefix}id__in": value}), Q()


@strawberry_django.filter_type(models.FilesystemShelve, description="A way to filter shelved items")
class FilesystemShelveFilter:

    @filter_field
    def ids(self, info, queryset, value: list[strawberry.ID], prefix: str):
        return queryset.filter(**{f"{prefix}id__in": value}), Q()


@strawberry_django.filter_type(models.MemoryShelve, description="A way to filter shelved items")
class MemoryShelveFilter:
    agent: strawberry.ID | None

    @filter_field
    def ids(self, info, queryset, value: list[strawberry.ID], prefix: str):
        return queryset.filter(**{f"{prefix}id__in": value}), Q()


@strawberry_django.filter_type(models.FileDrawer, description="A way to filter shelved items")
class FileDrawerFilter:
    shelve: strawberry.ID | None
    agent: strawberry.ID | None
    identifier: str | None

    @filter_field
    def ids(self, info, queryset, value: list[strawberry.ID], prefix: str):
        return queryset.filter(**{f"{prefix}id__in": value}), Q()


@strawberry_django.filter_type(models.MemoryDrawer, description="A way to filter shelved items")
class MemoryDrawerFilter:
    shelve: strawberry.ID | None
    agent: strawberry.ID | None

    @filter_field
    def implementation(self, info, queryset, value: strawberry.ID, prefix: str):
        return queryset.filter(**{f"{prefix}shelve__agent__implementations": value}), Q()

    @filter_field
    def identifier(self, info, queryset, value: str, prefix: str):
        return queryset.filter(**{f"{prefix}identifier": value}), Q()

    @filter_field
    def ids(self, info, queryset, value: list[strawberry.ID], prefix: str):
        return queryset.filter(**{f"{prefix}id__in": value}), Q()

    @filter_field
    def search(self, info, queryset, value: str, prefix: str):
        return queryset.filter(**{f"{prefix}label__icontains": value}), Q()


@strawberry_django.filter_type(models.Reservation, description="A way to filter reservations")
class ReservationFilter:
    waiter: WaiterFilter | None

    @filter_field
    def ids(self, info, queryset, value: list[strawberry.ID], prefix: str):
        return queryset.filter(**{f"{prefix}id__in": value}), Q()

    @filter_field
    def status(self, info, queryset, value: list[enums.ReservationStatus], prefix: str):
        return queryset.filter(**{f"{prefix}status__in": value}), Q()


@strawberry_django.order(models.Assignation)
class AssignationOrder:
    created_at: auto
    started_at: auto
    finished_at: auto
    status: auto


@strawberry_django.filter_type(models.Assignation)
class AssignationFilter:
    reservation: ReservationFilter | None

    @filter_field
    def ids(self, info, queryset, value: list[strawberry.ID], prefix: str):
        return queryset.filter(**{f"{prefix}id__in": value}), Q()

    @filter_field
    def status(self, info, queryset, value: list[enums.AssignationStatus], prefix: str):
        return queryset.filter(**{f"{prefix}status__in": value}), Q()

    @filter_field
    def instance_id(self, info, queryset, value: scalars.InstanceId, prefix: str):
        return queryset.filter(**{f"{prefix}reservation__waiter__instance_id": value}), Q()

    @filter_field
    def client_id(self, info, queryset, value: strawberry.ID, prefix: str):
        return queryset.filter(**{f"{prefix}agent__registry__client__client_id": value}), Q()

    @filter_field
    def state(self, info, queryset, value: list[enums.AssignationEventKind], prefix: str):
        return queryset.filter(**{f"{prefix}latest_event_kind__in": value}).distinct(), Q()

    @filter_field
    def implementation(self, info, queryset, value: strawberry.ID, prefix: str):
        return queryset.filter(**{f"{prefix}implementation_id": value}), Q()

    @filter_field
    def acted_on(self, info, queryset, value: list[str], prefix: str):
        return queryset.filter(**{f"{prefix}acted_on__overlap": value}), Q()

    @filter_field
    def created_before(self, info, queryset, value: datetime.datetime, prefix: str):
        return queryset.filter(**{f"{prefix}created_at__lt": value}), Q()

    @filter_field
    def created_after(self, info, queryset, value: datetime.datetime, prefix: str):
        return queryset.filter(**{f"{prefix}created_at__gt": value}), Q()

    @filter_field
    def agent(self, info, queryset, value: strawberry.ID, prefix: str):
        return queryset.filter(**{f"{prefix}agent_id": value}), Q()


@strawberry_django.order(models.AssignationEvent)
class AssignationEventOrder:
    created_at: auto


@strawberry_django.filter_type(models.AssignationEvent, description="A way to filter assignation events")
class AssignationEventFilter:

    @filter_field
    def kind(self, info, queryset, value: list[enums.AssignationEventKind], prefix: str):
        return queryset.filter(**{f"{prefix}kind__in": value}), Q()


@strawberry_django.filter_type(models.TestResult, description="A way to filter test results")
class TestResultFilter:
    name: Optional[FilterLookup[str]]

    @filter_field
    def ids(self, info, queryset, value: list[strawberry.ID], prefix: str):
        return queryset.filter(**{f"{prefix}id__in": value}), Q()


@strawberry_django.filter_type(models.Dependency)
class DependencyFilter:

    @filter_field
    def ids(self, info, queryset, value: list[strawberry.ID], prefix: str):
        return queryset.filter(**{f"{prefix}id__in": value}), Q()


@strawberry_django.filter_type(User)
class UserFilter:
    name: Optional[FilterLookup[str]]

    @filter_field
    def ids(self, info, queryset, value: list[strawberry.ID], prefix: str):
        return queryset.filter(**{f"{prefix}id__in": value}), Q()


@strawberry_django.order(User)
class UserOrder:
    name: auto
    email: auto
    date_joined: auto
    last_login: auto


@strawberry_django.order(Organization, description="A way to order registries")
class OrganizationOrder:
    slug: auto


@strawberry_django.filter_type(Organization, description="A way to filter organizations")
class OrganizationFilter:
    slug: Optional[FilterLookup[str]]

    @filter_field
    def ids(self, info, queryset, value: list[strawberry.ID], prefix: str):
        return queryset.filter(**{f"{prefix}id__in": value}), Q()


@strawberry_django.order(Client, description="A way to order apps")
class ClientOrder:
    defined_at: auto


@strawberry_django.filter_type(Client, description="A way to filter apps")
class ClientFilter:
    interface: Optional[FilterLookup[str]]

    @filter_field
    def ids(self, info, queryset, value: list[strawberry.ID], prefix: str):
        return queryset.filter(**{f"{prefix}id__in": value}), Q()

    @filter_field
    def has_implementations_for(self, info, queryset, value: list[rscalars.ActionHash], prefix: str):
        return queryset.filter(**{f"{prefix}registry__agents__implementations__action__hash__in": value}).distinct(), Q()

    @filter_field
    def mine(self, info, queryset, value: bool, prefix: str):
        return queryset.filter(**{f"{prefix}user_id": info.context.user.id}), Q()


@strawberry_django.order(models.Agent)
class AgentOrder:
    last_seen: auto


@strawberry_django.order(models.Action)
class ActionOrder:
    defined_at: auto
    used_at: auto

    def filter_used_at(self, queryset, info):
        if self.used_at is None:
            return queryset
        return queryset.annotate(latest_assignation_time=Max("assignation__created_at")).order_by("-latest_assignation_time")


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


@strawberry_django.filter_type(models.Protocol)
class ProtocolFilter:
    name: Optional[FilterLookup[str]]

    @filter_field
    def ids(self, info, queryset, value: list[strawberry.ID], prefix: str):
        return queryset.filter(**{f"{prefix}id__in": value}), Q()

    @filter_field
    def search(self, info, queryset, value: str, prefix: str):
        return queryset.filter(**{f"{prefix}name__icontains": value}), Q()


@strawberry_django.filter_type(models.Toolbox)
class ToolboxFilter:
    name: Optional[FilterLookup[str]]

    @filter_field
    def ids(self, info, queryset, value: list[strawberry.ID], prefix: str):
        return queryset.filter(**{f"{prefix}id__in": value}), Q()

    @filter_field
    def search(self, info, queryset, value: str, prefix: str):
        return queryset.filter(**{f"{prefix}name__icontains": value}), Q()


@strawberry_django.filter_type(models.Action)
class ShortcutActionFilter:

    @filter_field
    def search(self, info, queryset, value: str, prefix: str):
        return queryset.filter(**{f"{prefix}name__icontains": value}), Q()

    @filter_field
    def name(self, info, queryset, value: str, prefix: str):
        return queryset.filter(**{f"{prefix}name": value}), Q()

    @filter_field
    def ids(self, info, queryset, value: list[strawberry.ID], prefix: str):
        return queryset.filter(**{f"{prefix}id__in": value}), Q()

    @filter_field
    def demands(self, info, queryset, value: list[inputs.PortDemandInput], prefix: str):
        filtered_ids = None

        for ports_demand in value:
            new_ids = managers.get_action_ids_by_demands(
                ports_demand.matches,
                type=ports_demand.kind.value,
                force_length=ports_demand.force_length,
                force_non_nullable_length=ports_demand.force_non_nullable_length,
                force_structure_length=ports_demand.force_structure_length,
            )

            if filtered_ids is None:
                filtered_ids = set(new_ids)
            else:
                filtered_ids = filtered_ids.intersection(new_ids)

        if filtered_ids is None:
            return queryset, Q()

        return queryset.filter(**{f"{prefix}id__in": filtered_ids}), Q()

    @filter_field
    def kind(self, info, queryset, value: renums.ActionKind, prefix: str):
        return queryset.filter(**{f"{prefix}kind": value}), Q()

    @filter_field
    def protocols(self, info, queryset, value: list[str], prefix: str):
        return queryset.filter(**{f"{prefix}protocols__name__in": value}), Q()


@strawberry_django.filter_type(models.Shortcut)
class ShortcutFilter:

    @filter_field
    def search(self, info, queryset, value: str, prefix: str):
        return queryset.filter(**{f"{prefix}name__icontains": value}), Q()

    @filter_field
    def ids(self, info, queryset, value: list[strawberry.ID], prefix: str):
        return queryset.filter(**{f"{prefix}id__in": value}), Q()

    @filter_field
    def demands(self, info, queryset, value: list[inputs.PortDemandInput], prefix: str):
        filtered_ids = None

        for ports_demand in value:
            new_ids = managers.get_action_ids_by_demands(
                ports_demand.matches,
                type=ports_demand.kind.value,
                force_length=ports_demand.force_length,
                force_non_nullable_length=ports_demand.force_non_nullable_length,
                force_structure_length=ports_demand.force_structure_length,
                model="facade_shortcut",
            )

            if filtered_ids is None:
                filtered_ids = set(new_ids)
            else:
                filtered_ids = filtered_ids.intersection(new_ids)

        if filtered_ids is None:
            return queryset, Q()

        return queryset.filter(**{f"{prefix}id__in": filtered_ids}), Q()

    @filter_field
    def toolbox(self, info, queryset, value: strawberry.ID, prefix: str):
        return queryset.filter(**{f"{prefix}toolbox_id": value}), Q()


@strawberry_django.filter_type(models.HardwareRecord)
class HardwareRecordFilter:

    @filter_field
    def ids(self, info, queryset, value: list[strawberry.ID], prefix: str):
        return queryset.filter(**{f"{prefix}id__in": value}), Q()

    @filter_field
    def cpu_vendor_name(self, info, queryset, value: str, prefix: str):
        return queryset.filter(**{f"{prefix}cpu_vendor_name__contains": value}), Q()


@strawberry_django.filter_type(models.StructurePackage)
class StructurePackageFilter:

    @filter_field
    def ids(self, info, queryset, value: list[strawberry.ID], prefix: str):
        return queryset.filter(**{f"{prefix}id__in": value}), Q()

    @filter_field
    def search(self, info, queryset, value: str, prefix: str):
        return queryset.filter(
            Q(**{f"{prefix}key__icontains": value}) | Q(**{f"{prefix}description__icontains": value})
        ), Q()


@strawberry_django.filter_type(models.Structure)
class StructureFilter:

    @filter_field
    def ids(self, info, queryset, value: list[strawberry.ID], prefix: str):
        return queryset.filter(**{f"{prefix}id__in": value}), Q()

    @filter_field
    def search(self, info, queryset, value: str, prefix: str):
        return queryset.filter(
            Q(**{f"{prefix}key__icontains": value}) | Q(**{f"{prefix}description__icontains": value})
        ), Q()


@strawberry_django.filter_type(models.Interface)
class InterfaceFilter:

    @filter_field
    def ids(self, info, queryset, value: list[strawberry.ID], prefix: str):
        return queryset.filter(**{f"{prefix}id__in": value}), Q()

    @filter_field
    def search(self, info, queryset, value: str, prefix: str):
        return queryset.filter(
            Q(**{f"{prefix}key__icontains": value}) | Q(**{f"{prefix}description__icontains": value})
        ), Q()


@strawberry_django.filter_type(models.InputInterfaceUsage)
class InputInterfaceUsageFilter:

    @filter_field
    def ids(self, info, queryset, value: list[strawberry.ID], prefix: str):
        return queryset.filter(**{f"{prefix}id__in": value}), Q()

    @filter_field
    def interface(self, info, queryset, value: strawberry.ID, prefix: str):
        return queryset.filter(**{f"{prefix}interface__id": value}), Q()


@strawberry_django.filter_type(models.OutputInterfaceUsage)
class OutputInterfaceUsageFilter:

    @filter_field
    def ids(self, info, queryset, value: list[strawberry.ID], prefix: str):
        return queryset.filter(**{f"{prefix}id__in": value}), Q()

    @filter_field
    def interface(self, info, queryset, value: strawberry.ID, prefix: str):
        return queryset.filter(**{f"{prefix}interface__id": value}), Q()


@strawberry_django.filter_type(models.InputStructureUsage)
class InputStructureUsageFilter:

    @filter_field
    def ids(self, info, queryset, value: list[strawberry.ID], prefix: str):
        return queryset.filter(**{f"{prefix}id__in": value}), Q()

    @filter_field
    def structure(self, info, queryset, value: strawberry.ID, prefix: str):
        return queryset.filter(**{f"{prefix}structure__id": value}), Q()


@strawberry_django.filter_type(models.OutputStructureUsage)
class OutputStructureUsageFilter:

    @filter_field
    def ids(self, info, queryset, value: list[strawberry.ID], prefix: str):
        return queryset.filter(**{f"{prefix}id__in": value}), Q()

    @filter_field
    def structure(self, info, queryset, value: strawberry.ID, prefix: str):
        return queryset.filter(**{f"{prefix}structure__id": value}), Q()


@strawberry_django.filter_type(models.Action)
class ActionFilter:
    name: Optional[FilterLookup[str]]

    @filter_field
    def search(self, info, queryset, value: str, prefix: str):
        return queryset.filter(**{f"{prefix}name__icontains": value}), Q()

    @filter_field
    def ids(self, info, queryset, value: list[strawberry.ID], prefix: str):
        return queryset.filter(**{f"{prefix}id__in": value}), Q()

    @filter_field
    def demands(self, info, queryset, value: list[inputs.PortDemandInput], prefix: str):
        if len(value) == 0:
            return queryset, Q()

        filtered_ids = None

        for ports_demand in value:
            new_ids = managers.get_action_ids_by_demands(
                ports_demand.matches,
                type=ports_demand.kind.value,
                force_length=ports_demand.force_length,
                force_non_nullable_length=ports_demand.force_non_nullable_length,
                force_structure_length=ports_demand.force_structure_length,
            )

            if filtered_ids is None:
                filtered_ids = set(new_ids)
            else:
                filtered_ids = filtered_ids.intersection(new_ids)

        if filtered_ids is None:
            return queryset, Q()

        return queryset.filter(**{f"{prefix}id__in": filtered_ids}), Q()

    @filter_field
    def protocols(self, info, queryset, value: list[str], prefix: str):
        return queryset.filter(**{f"{prefix}protocols__name__in": value}), Q()

    @filter_field
    def kind(self, info, queryset, value: renums.ActionKind, prefix: str):
        return queryset.filter(**{f"{prefix}kind": value}), Q()

    @filter_field
    def in_collection(self, info, queryset, value: str, prefix: str):
        return queryset.filter(**{f"{prefix}collections__name": value}), Q()

    @filter_field
    def used_before(self, info, queryset, value: datetime.datetime, prefix: str):
        return queryset.filter(**{f"{prefix}assignations__created_at__lt": value}), Q()

    @filter_field
    def used_after(self, info, queryset, value: datetime.datetime, prefix: str):
        return queryset.filter(**{f"{prefix}assignations__created_at__gt": value}), Q()

    @filter_field
    def stateful(self, info, queryset, value: bool, prefix: str):
        return queryset.filter(**{f"{prefix}stateful": value}), Q()

    @filter_field(description="Filter using app identifier")
    def app_identifier(self, info, queryset, value: str, prefix: str):
        return queryset.filter(**{f"{prefix}app__identifier": value}), Q()


@strawberry_django.filter_type(models.Agent)
class ImplementationAgentFilter:

    @filter_field
    def client_id(self, info, queryset, value: str, prefix: str):
        return queryset.filter(**{f"{prefix}registry__app__client_id": value}), Q()

    @filter_field
    def ids(self, info, queryset, value: list[strawberry.ID], prefix: str):
        return queryset.filter(**{f"{prefix}id__in": value}), Q()

    @filter_field
    def instance_id(self, info, queryset, value: str, prefix: str):
        return queryset.filter(**{f"{prefix}instance_id": value}), Q()

    @filter_field
    def extensions(self, info, queryset, value: list[str], prefix: str):
        return queryset.filter(**{f"{prefix}extensions__contains": value}), Q()

    @filter_field
    def has_implementations(self, info, queryset, value: list[str], prefix: str):
        return queryset.filter(**{f"{prefix}implementations__action__hash__in": value}), Q()

    @filter_field
    def has_states(self, info, queryset, value: list[str], prefix: str):
        return queryset.filter(**{f"{prefix}states__state_schema__hash__in": value}), Q()


@strawberry_django.filter_type(models.Action)
class ImplementationActionFilter:

    @filter_field
    def search(self, info, queryset, value: str, prefix: str):
        return queryset.filter(**{f"{prefix}name__icontains": value}), Q()

    @filter_field
    def name(self, info, queryset, value: str, prefix: str):
        return queryset.filter(**{f"{prefix}name": value}), Q()

    @filter_field
    def ids(self, info, queryset, value: list[strawberry.ID], prefix: str):
        return queryset.filter(**{f"{prefix}id__in": value}), Q()

    @filter_field
    def demands(self, info, queryset, value: list[inputs.PortDemandInput], prefix: str):
        filtered_ids = None

        for ports_demand in value:
            new_ids = managers.get_action_ids_by_demands(
                ports_demand.matches,
                type=ports_demand.kind.value,
                force_length=ports_demand.force_length,
                force_non_nullable_length=ports_demand.force_non_nullable_length,
                force_structure_length=ports_demand.force_structure_length,
            )

            if filtered_ids is None:
                filtered_ids = set(new_ids)
            else:
                filtered_ids = filtered_ids.intersection(new_ids)

        if filtered_ids is None:
            return queryset, Q()

        return queryset.filter(**{f"{prefix}id__in": filtered_ids}), Q()

    @filter_field
    def kind(self, info, queryset, value: renums.ActionKind, prefix: str):
        return queryset.filter(**{f"{prefix}kind": value}), Q()

    @filter_field
    def protocols(self, info, queryset, value: list[str], prefix: str):
        return queryset.filter(**{f"{prefix}protocols__name__in": value}), Q()


@strawberry.input
class ParamPair:
    key: str
    value: str


@strawberry_django.order(models.Implementation)
class ImplementationOrder:
    created_at: auto
    started_at: auto
    finished_at: auto
    status: auto


@strawberry_django.filter_type(models.Implementation)
class ImplementationFilter:
    interface: Optional[FilterLookup[str]]
    action: ImplementationActionFilter | None
    agent: ImplementationAgentFilter | None

    @filter_field
    def ids(self, info, queryset, value: list[strawberry.ID], prefix: str):
        return queryset.filter(**{f"{prefix}id__in": value}), Q()

    @filter_field
    def action_hash(self, info, queryset, value: rscalars.ActionHash, prefix: str):
        return queryset.filter(**{f"{prefix}action__hash": value}), Q()

    @filter_field
    def extension(self, info, queryset, value: str, prefix: str):
        return queryset.filter(**{f"{prefix}extension": value}), Q()

    @filter_field
    def parameters(self, info, queryset, value: list[ParamPair], prefix: str):
        for param in value:
            queryset = queryset.filter(**{f"{prefix}params__contains": {param.key: param.value}})
        return queryset, Q()

    @filter_field
    def resolvable_for(self, info, queryset, value: strawberry.ID, prefix: str):
        dependency = models.Dependency.objects.get(id=value)
        return queryset.filter(**{f"{prefix}action__app__identifier": dependency.app_filter}), Q()

    @filter_field
    def search(self, info, queryset, value: str, prefix: str):
        return queryset.filter(
            Q(**{f"{prefix}action__name__icontains": value})
            | Q(**{f"{prefix}agent__name__icontains": value})
            | Q(**{f"{prefix}interface__icontains": value})
        ), Q()

    @filter_field
    def action_demand(self, info, queryset, value: inputs.ActionDemandInput, prefix: str):
        new_ids = managers.get_action_ids_by_action_demand(
            action_demand=value,
            organization_id=info.context.request.organization.id,
        )
        return queryset.filter(**{f"{prefix}action__id__in": new_ids}), Q()
