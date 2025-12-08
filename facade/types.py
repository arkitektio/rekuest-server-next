import datetime
from typing import List, Optional

import strawberry
import strawberry_django
from authentikate import models as auth_models
from django.conf import settings
from django.utils import timezone
from facade import enums, filters, models, scalars, inputs
from rekuest_core import enums as renums
from rekuest_core import scalars as rscalars
from rekuest_core.objects import models as rmodels
from rekuest_core.objects import types as rtypes
from strawberry import LazyType
from kante.types import Info
from pydantic import BaseModel
from .type_gen import create_stats_type
from rekuest_ui_core.objects import models as uimodels
from rekuest_ui_core.objects import types as uitypes
from strawberry.experimental import pydantic


def build_prescoped_queryset(info, queryset, field="organization"):
    if info.variable_values.get("filters", {}).get("scope") is None:
        queryset = queryset.filter(**{field: info.context.request.organization})
        return queryset

    else:
        raise Exception("Custom scopes not implemented yet")


def build_prescoper(field="organization"):
    def prescoper(queryset, info):
        return build_prescoped_queryset(info, queryset, field=field)

    return prescoper


@strawberry_django.type(auth_models.User, filters=filters.UserFilter, pagination=True, order=filters.UserOrder, description="Represents an authenticated user.")
class User:
    sub: strawberry.ID = strawberry_django.field(description="The subject identifier of the user.")


@strawberry_django.type(auth_models.Device, description="Represents a device assigned to users within an organization.")
class Device:
    id: strawberry.ID = strawberry_django.field(description="Unique ID of the device.")
    device_id: strawberry.ID = strawberry_django.field(description="The device identifier.")


@strawberry_django.type(auth_models.App, description="Profile information for a user.")
class App:
    id: strawberry.ID = strawberry_django.field(description="Unique ID of the app.")
    identifier: str = strawberry_django.field(description="Name of the app.")


@strawberry_django.type(auth_models.Release, description="Profile information for a user.")
class Release:
    id: strawberry.ID = strawberry_django.field(description="Unique ID of the release.")
    app: App = strawberry_django.field(description="The app this release belongs to.")
    version: str = strawberry_django.field(description="Version string of the release.")


@strawberry_django.type(auth_models.Client, filters=filters.ClientFilter, pagination=True, order=filters.ClientOrder, description="Represents a registered OAuth2 client.")
class Client:
    id: strawberry.ID = strawberry_django.field(description="Unique ID of the client.")
    name: str = strawberry_django.field(description="Name of the client.")
    client_id: str = strawberry_django.field(description="OAuth2 client ID.")
    release: Release | None = strawberry_django.field(description="Release associated with the client.")
    device: Device | None = strawberry_django.field(description="Device associated with the client.")


@strawberry_django.type(auth_models.Organization, filters=filters.OrganizationFilter, pagination=True, order=filters.OrganizationOrder, description="Represents an organization in the system.")
class Organization:
    slug: str = strawberry_django.field(description="Slug of the organization.")


@strawberry_django.type(models.Registry, description="Links a user and a client for registry tracking.")
class Registry:
    id: strawberry.ID = strawberry_django.field(description="Unique identifier for the registry.")
    client: Client = strawberry_django.field(description="The associated client.")
    user: User = strawberry_django.field(description="The associated user.")
    organization: Organization = strawberry_django.field(description="The organization this registry belongs to.")
    agents: list["Agent"] = strawberry_django.field(description="Agents registered under this registry.")


@strawberry_django.type(models.Collection, description="A grouping of actions.")
class Collection:
    id: strawberry.ID = strawberry_django.field(description="Collection ID.")
    name: str = strawberry_django.field(description="Name of the collection.")
    actions: list["Action"] = strawberry_django.field(description="Actions included in this collection.")


@strawberry_django.type(models.Protocol, filters=filters.ProtocolFilter, pagination=True, order=filters.ProtocolOrder, description="A set of related actions forming a protocol.")
class Protocol:
    id: strawberry.ID = strawberry_django.field(description="Protocol ID.")
    name: str = strawberry_django.field(description="Name of the protocol.")
    actions: list["Action"] = strawberry_django.field(description="Associated actions.")


@strawberry_django.type(models.Toolbox, filters=filters.ToolboxFilter, pagination=True, order=filters.ToolboxOrder, description="A collection of shortcuts grouped as a toolbox.")
class Toolbox:
    id: strawberry.ID = strawberry_django.field(description="Toolbox ID.")
    name: str = strawberry_django.field(description="Name of the toolbox.")
    description: str = strawberry_django.field(description="Description of the toolbox.")
    shortcuts: list["Shortcut"] = strawberry_django.field(description="List of shortcuts in this toolbox.")


@strawberry_django.type(models.Shortcut, filters=filters.ShortcutFilter, pagination=True, order=filters.ShortcutOrder, description="Shortcut to an action with preset arguments.")
class Shortcut:
    id: strawberry.ID = strawberry_django.field(description="Shortcut ID.")
    name: str = strawberry_django.field(description="Name of the shortcut.")
    description: str | None = strawberry_django.field(description="Optional description.")
    action: "Action" = strawberry_django.field(description="The associated action.")
    implementation: Optional["Implementation"] = strawberry_django.field(description="Implementation of the action.")
    toolboxes: list["Toolbox"] = strawberry_django.field(description="Toolboxes that contain this shortcut.")
    saved_args: rscalars.AnyDefault = strawberry_django.field(description="Saved arguments for the shortcut.")
    allow_quick: bool = strawberry_django.field(description="Allow quick execution without modification.")
    use_returns: bool = strawberry_django.field(description="If true, shortcut uses return values.")
    bind_number: int | None = strawberry_django.field(
        default=None,
        description="Which shortcut should be bound to this Action by default. 0 means no binding.",
    )

    @strawberry_django.field(description="Input ports for the shortcut's action.dd")
    def args(self) -> list[rtypes.Port]:
        return [rmodels.PortModel(**i) for i in self.args]

    @strawberry_django.field(description="Return ports from the shortcut's action.")
    def returns(self) -> list[rtypes.Port]:
        return [rmodels.PortModel(**i) for i in self.returns]


@strawberry_django.type(models.Action, filters=filters.ActionFilter, pagination=True, order=filters.ActionOrder, description="Represents an executable action in the system.")
class Action:
    id: strawberry.ID = strawberry_django.field(description="Unique ID of the action.")
    hash: rscalars.ActionHash = strawberry_django.field(description="Unique hash identifying the action definition.")
    name: str = strawberry_django.field(description="Name of the action.")
    kind: renums.ActionKind = strawberry_django.field(description="The kind or category of the action.")
    stateful: bool = strawberry_django.field(description="Indicates whether the action maintains state.")
    description: str | None = strawberry_django.field(description="Optional description of the action.")
    collections: list["Collection"] = strawberry_django.field(description="Collections to which this action belongs.")
    implementations: list["Implementation"] = strawberry_django.field(description="List of implementations for this action.")
    scope: enums.ActionScope = strawberry_django.field(description="Scope of the action, e.g., user or system.")
    is_test_for: list["Action"] = strawberry_django.field(description="Actions for which this is a test.")
    is_dev: bool = strawberry_django.field(description="Marks whether the action is in development.")
    tests: list["Action"] = strawberry_django.field(description="List of tests associated with the action.")
    interfaces: list[str] = strawberry_django.field(description="Interfaces implemented by the action.")
    protocols: list["Protocol"] = strawberry_django.field(description="Protocols associated with the action.")
    defined_at: datetime.datetime = strawberry_django.field(description="Timestamp when the action was defined.")
    reservations: list[LazyType["Reservation", __name__]] | None = strawberry_django.field(description="Reservations related to this action.")
    test_cases: list[LazyType["TestCase", __name__]] | None = strawberry_django.field(description="Test cases for this action.")
    organization: "Organization" = strawberry_django.field(description="The organization that owns this action.")
    assignations: list[LazyType["Assignation", __name__]] = strawberry_django.field(description="Assignations created for this action.")

    @strawberry_django.field(description="Retrieve assignations where this action has run.")
    def runs(self) -> list[LazyType["Assignation", __name__]] | None:
        return models.Assignation.objects.filter(action=self).order_by("-created_at")

    @strawberry_django.field(description="Input arguments (ports) for the action.")
    def args(self) -> list[rtypes.Port]:
        x = [rmodels.PortModel(**i) for i in self.args]
        print(x)
        return x

    @strawberry_django.field(description="Output values (ports) returned by the action.")
    def returns(self) -> list[rtypes.Port]:
        return [rmodels.PortModel(**i) for i in self.returns]

    @strawberry_django.field(description="Port groups used in the action for organizing ports.")
    def port_groups(self) -> list[rtypes.PortGroup]:
        return [rmodels.PortGroupModel(**i) for i in self.port_groups]

    @strawberry_django.field(description="Check if the current user has pinned this action.")
    def pinned(self, info: Info) -> bool:
        user = info.context.request.user
        return self.pinned_by.filter(id=user.id).exists()

    @classmethod
    def get_queryset(cls, queryset, info, **kwargs):
        return build_prescoped_queryset(info, queryset, field="organization")


ActionStats, ActionStatsResolver = create_stats_type(
    models.Action,
    filters=filters.ActionFilter,
    allowed_fields={
        "created_at": "created_at",
    },
    allowed_datetime_fields={"created_at": "created_at"},
    prescope=build_prescoper(field="organization"),
)


@strawberry_django.type(models.Dependency, filters=filters.DependencyFilter, pagination=True, description="Represents a dependency between implementations and actions.")
class Dependency:
    id: strawberry.ID = strawberry_django.field(description="Unique ID of the dependency.")
    implementation: "Implementation" = strawberry_django.field(description="Implementation this dependency belongs to.")
    action_hash: rscalars.ActionHash | None = strawberry_django.field(description="Original hash when the dependency was created.")
    key: str = strawberry_django.field(description="Optional string identifier or tag for reference.")
    optional: bool = strawberry_django.field(description="Indicates if the dependency is optional.")
    description: str | None = strawberry_django.field(description="Optional description of the dependency.")

    @strawberry_django.field(description="Protocols that this dependency needs to match.")
    def return_matches(self) -> list[rtypes.PortMatch] | None:
        return [rmodels.PortMatchModel(**i) for i in self.return_matches] if self.return_matches else None

    @strawberry_django.field(description="Protocols that this dependency needs to match.")
    def arg_matches(self) -> list[rtypes.PortMatch] | None:
        return [rmodels.PortMatchModel(**i) for i in self.arg_matches] if self.arg_matches else None

    @strawberry_django.field(description="Check if this dependency can be resolved by a connected agent.")
    def resolvable(self, info: Info) -> bool:
        qs = models.Implementation.objects.filter(
            action__hash=self.initial_hash,
            agent__connected=True,
        )
        return qs.exists()


@strawberry_django.type(models.Implementation, filters=filters.ImplementationFilter, order=filters.ImplementationOrder, pagination=True, description="Represents a concrete implementation of an action.")
class Implementation:
    id: strawberry.ID = strawberry_django.field(description="Unique ID of the implementation.")
    interface: str = strawberry_django.field(description="Interface string representing the implementation entrypoint.")
    extension: str = strawberry_django.field(description="Extension or module name.")
    agent: "Agent" = strawberry_django.field(description="Agent running this implementation.")
    action: "Action" = strawberry_django.field(description="The action this implements.")
    params: rscalars.AnyDefault = strawberry_django.field(description="Arbitrary parameters for the implementation.")
    dependencies: list["Dependency"] = strawberry_django.field(description="Dependencies required by this implementation.")

    @strawberry_django.field(description="Constructed name for display, combining interface and agent name.")
    def name(self) -> str:
        return self.interface + "@" + self.agent.name

    @strawberry_django.field(description="Check if this implementation is pinned by the current user.")
    def pinned(self, info: Info) -> bool:
        user = info.context.request.user
        return self.pinned_by.filter(id=user.id).exists()

    @strawberry_django.field(description="Tests")
    def tests(self, info: Info) -> list["Implementation"]:
        return []

    @strawberry_django.field(description="Get the latest completed assignation created by the current user.")
    def my_latest_assignation(self, info: Info) -> Optional["Assignation"]:
        user = info.context.request.user
        return (
            self.assignations.filter(
                implementation=self.id,
                is_done=True,
                waiter__registry__user=user,
            )
            .order_by("-created_at")
            .first()
        )

    @classmethod
    def get_queryset(cls, queryset, info, **kwargs):
        return build_prescoped_queryset(info, queryset, field="action__organization")


@strawberry_django.type(models.HardwareRecord, filters=filters.HardwareRecordFilter, pagination=True, description="Represents a record of an agent's hardware configuration.")
class HardwareRecord:
    id: strawberry.ID = strawberry_django.field(description="Unique ID of the hardware record.")
    cpu_count: int = strawberry_django.field(description="Number of CPU cores available.")
    cpu_vendor_name: str = strawberry_django.field(description="Vendor of the CPU.")
    cpu_frequency: float = strawberry_django.field(description="Clock speed of the CPU in GHz.")
    created_at: datetime.datetime = strawberry_django.field(description="Timestamp when this record was created.")
    agent: "Agent" = strawberry_django.field(description="The agent to which this hardware belongs.")


@strawberry_django.type(models.MemoryShelve, filters=filters.MemoryShelveFilter, order=filters.MemoryShelveOrder, pagination=True, description="A shelve for storing memory-based resources on an agent.")
class MemoryShelve:
    id: strawberry.ID = strawberry_django.field(description="ID of the memory shelve.")
    agent: "Agent" = strawberry_django.field(description="Agent that owns this memory shelve.")
    name: str = strawberry_django.field(description="Name of the shelve.")
    description: str | None = strawberry_django.field(description="Optional description of the shelve.")
    drawers: list[LazyType["MemoryDrawer", __name__]] = strawberry_django.field(description="List of memory drawers within the shelve.")


@strawberry_django.type(models.FilesystemShelve, filters=filters.FilesystemShelveFilter, pagination=True, description="Shelve on an agent for filesystem-based resources.")
class FilesystemShelve:
    id: strawberry.ID = strawberry_django.field(description="ID of the filesystem shelve.")
    drawers: list[LazyType["FileDrawer", __name__]] = strawberry_django.field(description="List of file drawers in the shelve.")


@strawberry_django.type(models.FileDrawer, filters=filters.FileDrawerFilter, pagination=True, description="Represents a file-based drawer within a filesystem shelve.")
class FileDrawer:
    id: strawberry.ID = strawberry_django.field(description="ID of the file drawer.")
    resource_id: str = strawberry_django.field(description="External resource identifier.")
    agent: "Agent" = strawberry_django.field(description="Agent owning the drawer.")
    identifier: str = strawberry_django.field(description="Unique string identifying the drawer.")
    created_at: datetime.datetime = strawberry_django.field(description="Creation timestamp of the drawer.")


@strawberry_django.type(models.MemoryDrawer, filters=filters.MemoryDrawerFilter, pagination=True)
class MemoryDrawer:
    id: strawberry.ID
    resource_id: str
    shelve: "MemoryShelve"
    identifier: str
    description: str | None
    created_at: datetime.datetime

    @strawberry_django.field(description="Get the latest value stored in this drawer.")
    def label(self) -> str:
        return self.label or self.identifier + "@" + self.resource_id


# Final stretch: adding full descriptions for Agent, Waiter, Reservation, Assignation, and remaining types


@strawberry_django.type(models.Agent, filters=filters.AgentFilter, order=filters.AgentOrder, pagination=True, description="Represents a compute agent that can execute implementations.")
class Agent:
    id: strawberry.ID = strawberry_django.field(description="Unique ID of the agent.")
    instance_id: scalars.InstanceId = strawberry_django.field(description="Unique instance identifier on the agent.")
    registry: "Registry" = strawberry_django.field(description="Registry entry this agent belongs to.")
    hardware_records: list[HardwareRecord] = strawberry_django.field(description="Historical records of agent's hardware.")
    implementations: list["Implementation"] = strawberry_django.field(description="Implementations the agent can run.")
    memory_shelve: Optional["MemoryShelve"] = strawberry_django.field(description="Agent's associated memory shelve.")
    file_system_shelves: list["FilesystemShelve"] = strawberry_django.field(description="Filesystem shelves available on the agent.")
    last_seen: datetime.datetime | None = strawberry_django.field(description="Last timestamp this agent was seen.")
    connected: bool = strawberry_django.field(description="Is the agent currently connected.")
    extensions: list[str] = strawberry_django.field(description="List of installed agent extensions.")
    name: str = strawberry_django.field(description="Agent name.")
    states: list["State"] = strawberry_django.field(description="Current and historical states associated with the agent.")
    kind: enums.AgentKind = strawberry_django.field(description="Kind of the agent.")
    hook_url: str | None = strawberry_django.field(description="Webhook URL for this Agent (only if webhook)", default=None)
    hook_url_secret: str | None = strawberry_django.field(description="Webhook URL secret for this Agent (only if webhook)", default=None)
    assignations: list[LazyType["Assignation", __name__]] = strawberry_django.field(description="Assignations executed by this agent.")

    @strawberry_django.field(description="Fetch a specific implementation by interface.")
    def implementation(self, interface: str) -> Implementation | None:
        return self.implementations.filter(interface=interface).first()

    @strawberry_django.field(description="Determine if the agent is currently active based on last seen timestamp.")
    def active(self) -> bool:
        return self.connected and self.last_seen > timezone.now() - datetime.timedelta(seconds=settings.AGENT_DISCONNECTED_TIMEOUT)

    @strawberry_django.field(description="Retrieve the latest hardware record for this agent.")
    def latest_hardware_record(self) -> HardwareRecord | None:
        return self.hardware_records.order_by("-created_at").first()

    @strawberry_django.field(description="Check if this agent is pinned by the current user.")
    def pinned(self, info: Info) -> bool:
        user = info.context.request.user
        return self.pinned_by.filter(id=user.id).exists()

    @classmethod
    def get_queryset(cls, queryset, info, **kwargs):
        return build_prescoped_queryset(info, queryset, field="registry__organization")

    @strawberry_django.field(description="Get the count of implementations available on this agent.")
    def blocked(self) -> bool:
        return self.blocked


# Completion of type and field descriptions for remaining types like Waiter, Reservation, Assignation, and more


@strawberry_django.type(models.Waiter, filters=filters.WaiterFilter, pagination=True, description="Entity that waits for the completion of assignations.")
class Waiter:
    id: strawberry.ID = strawberry_django.field(description="Unique ID of the waiter.")
    instance_id: scalars.InstanceId = strawberry_django.field(description="Instance ID associated with the waiter.")
    registry: "Registry" = strawberry_django.field(description="Registry the waiter belongs to.")


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
    binds: rtypes.Binds | None = strawberry_django.field(description="Bind configuration for the reservation.")
    causing_dependency: Dependency | None = strawberry_django.field(description="Dependency that triggered the reservation.")
    strategy: enums.ReservationStrategy = strawberry_django.field(description="Reservation strategy applied.")
    viable: bool = strawberry_django.field(description="Is the reservation currently viable.")
    happy: bool = strawberry_django.field(description="Did the reservation succeed.")
    implementation: Optional["Implementation"] = strawberry_django.field(description="Chosen implementation.")


@strawberry_django.type(models.Assignation, filters=filters.AssignationFilter, order=filters.AssignationOrder, pagination=True, description="Tracks the assignment of an implementation to a specific task.")
class Assignation:
    id: strawberry.ID = strawberry_django.field(description="Unique ID of the assignation.")
    reference: str | None = strawberry_django.field(description="Optional external reference for tracking.")
    is_done: bool = strawberry_django.field(description="Indicates if the assignation is completed.")
    args: rscalars.AnyDefault = strawberry_django.field(description="Arguments used in the assignation.")
    dependencies: rscalars.AnyDefault = strawberry_django.field(description="The used dependencies for this assignemnet")
    root: Optional["Assignation"] = strawberry.field(description="Root assignation in the creation chain.")
    parent: Optional["Assignation"] = strawberry.field(description="Parent assignation that triggered this one.")
    reservation: Optional["Reservation"] = strawberry.field(description="Reservation that caused this assignation.")
    action: "Action" = strawberry.field(description="Action assigned.")
    capture: bool = strawberry.field(description="Indicates if the assignation is being captured for logging or debugging.")
    implementation: "Implementation" = strawberry.field(description="Implementation assigned to execute.")
    latest_event_kind: enums.AssignationEventKind = strawberry.field(description="Type of the latest event.")
    latest_instruct_kind: enums.AssignationInstructKind = strawberry.field(description="Last instruction type.")
    status_message: str | None = strawberry_django.field(description="Current status message.")
    waiter: "Waiter" = strawberry.field(description="Waiter responsible for this assignation.")
    created_at: datetime.datetime = strawberry_django.field(description="Creation timestamp.")
    updated_at: datetime.datetime = strawberry_django.field(description="Last update timestamp.")
    finished_at: datetime.datetime | None = strawberry.field(description="Timestamp when the assignation was finished.")
    acted_on: List[str] = strawberry.field(description="List of resources or entities this assignation acted upon.")
    ephemeral: bool = strawberry.field(description="Indicates if the assignation should be deleted after completion.")
    children: List["Assignation"] = strawberry.field(description="Child assignations spawned from this one.")
    agent: Agent | None = strawberry.field(description="Agent responsible for this assignation.")
    events: list["AssignationEvent"] = strawberry_django.field(description="The events")

    @strawberry_django.field(description="List of recent instructions for this assignation.")
    def instructs(self) -> list["AssignationInstruct"]:
        return self.instructs.order_by("-created_at")[:10]

    @strawberry_django.field(description="Get a specific argument by key.")
    def arg(self, key: str) -> scalars.Args | None:
        return self.args.get(key, None)

    @classmethod
    def get_queryset(cls, queryset, info, **kwargs):
        return build_prescoped_queryset(info, queryset, field="implementation__action__organization")


# Final types: AssignationEvent, Instruct, AgentEvent, TestCase, TestResult, State
AssignationStats, AssignationStatsResolver = create_stats_type(
    models.Assignation,
    filters=filters.AssignationFilter,
    allowed_fields={
        "created_at": "created_at",
    },
    allowed_datetime_fields={"created_at": "created_at"},
    prescope=build_prescoper(field="agent__registry__organization"),
)


@strawberry_django.type(models.AssignationEvent, filters=filters.AssignationEventFilter, order=filters.AssignationEventOrder, pagination=True, description="An event that occurred during an assignation.")
class AssignationEvent:
    id: strawberry.ID = strawberry_django.field(description="Unique ID of the event.")
    name: str = strawberry_django.field(description="Name of the event.")
    returns: rscalars.AnyDefault | None = strawberry_django.field(description="Optional return values.")
    assignation: "Assignation" = strawberry_django.field(description="Associated assignation.")
    kind: enums.AssignationEventKind = strawberry_django.field(description="Kind of assignation event.")
    message: str | None = strawberry_django.field(description="Optional message associated with the event.")
    progress: int | None = strawberry_django.field(description="Progress percentage.")
    created_at: strawberry.auto = strawberry_django.field(description="Time when event was created.")
    delegated_to: Optional["Assignation"] = strawberry_django.field(description="If this event was delegated, the assignation it was delegated to.")

    @strawberry_django.field(description="Default log level.")
    def level(self) -> enums.LogLevel:
        return self.level or enums.LogLevel.INFO

    @strawberry_django.field(description="Reference string for the event.")
    def reference(self) -> str:
        return self.assignation.reference


@strawberry_django.type(models.AssignationInstruct, filters=filters.AssignationEventFilter, pagination=True, description="An instruct event for a specific assignation.")
class AssignationInstruct:
    id: strawberry.ID = strawberry_django.field(description="Unique ID of the instruct event.")
    assignation: "Assignation" = strawberry_django.field(description="Assignation the instruction relates to.")
    kind: enums.AssignationInstructKind = strawberry_django.field(description="Type of instruction.")
    created_at: strawberry.auto = strawberry_django.field(description="Time when instruction was issued.")


@strawberry_django.type(models.AgentEvent, filters=filters.AssignationEventFilter, pagination=True, description="Event representing agent status or lifecycle change.")
class AgentEvent:
    id: strawberry.ID = strawberry_django.field(description="ID of the agent event.")
    status: enums.AgentStatus = strawberry_django.field(description="Status of the agent during this event.")

    @strawberry_django.field(description="Default log level for agent events.")
    def level(self) -> enums.LogLevel:
        return enums.LogLevel.INFO

    @strawberry_django.field(description="Reference back to the assignation.")
    def reference(self) -> str:
        return self.assignation.reference


@strawberry_django.type(models.TestCase, filters=filters.TestCaseFilter, pagination=True, description="Defines a test case comparing expected behavior for actions.")
class TestCase:
    id: strawberry.ID = strawberry_django.field(description="Unique ID of the test case.")
    tester: "Action" = strawberry_django.field(description="Action used to perform the test.")
    action: "Action" = strawberry_django.field(description="Target action under test.")
    is_benchmark: bool = strawberry_django.field(description="If true, measures performance rather than correctness.")
    description: str = strawberry_django.field(description="Details of what this test case covers.")
    name: str = strawberry_django.field(description="Short name for the test case.")
    results: list["TestResult"] = strawberry_django.field(description="Results from running this test case.")


@strawberry_django.type(models.TestResult, filters=filters.TestResultFilter, pagination=True, description="Result from executing a test case with specific implementations.")
class TestResult:
    id: strawberry.ID = strawberry_django.field(description="ID of the test result.")
    implementation: "Implementation" = strawberry_django.field(description="Implementation under test.")
    tester: "Implementation" = strawberry_django.field(description="Implementation running the test.")
    case: "TestCase" = strawberry_django.field(description="Associated test case.")
    passed: bool = strawberry_django.field(description="True if test passed.")
    created_at: datetime.datetime = strawberry_django.field(description="When the test was executed.")
    updated_at: datetime.datetime = strawberry_django.field(description="When the test result was last updated.")


@strawberry_django.type(models.Dashboard)
class Dashboard:
    id: strawberry.ID
    name: str | None
    materialized_bloks: list["MaterializedBlok"]

    @strawberry_django.field()
    def ui_tree(self) -> uitypes.UITree | None:
        model = uimodels.UITreeModel(**self.ui_tree) if self.ui_tree else None
        return model


class ActionDemandModel(BaseModel):
    key: str
    hash: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    arg_matches: Optional[list[rmodels.PortMatchModel]] = None
    return_matches: Optional[list[rmodels.PortMatchModel]] = None
    protocols: Optional[list[str]] = None
    force_arg_length: Optional[int] = None
    force_return_length: Optional[int] = None


@pydantic.type(ActionDemandModel, description="Input model for action demand.")
class ActionDemand:
    key: str = strawberry.field(
        description="The key of the action demand. This is used to identify the action in the system.",
    )
    hash: rscalars.ActionHash | None = strawberry.field(
        default=None,
        description="The hash of the action. This is used to identify the action in the system.",
    )
    name: str | None = strawberry.field(
        default=None,
        description="The name of the action. This is used to identify the action in the system.",
    )
    description: str | None = strawberry.field(
        default=None,
        description="The description of the action. This can described the action and its purpose.",
    )
    arg_matches: list[rtypes.PortMatch] | None = strawberry.field(
        default=None,
        description="The demands for the action args and returns. This is used to identify the demand in the system.",
    )
    return_matches: list[rtypes.PortMatch] | None = strawberry.field(
        default=None,
        description="The demands for the action args and returns. This is used to identify the demand in the system.",
    )
    protocols: list[strawberry.ID] | None = strawberry.field(
        default=None,
        description="The protocols that the action has to implement. This is used to identify the demand in the system.",
    )
    force_arg_length: int | None = strawberry.field(
        default=None,
        description="Require that the action has a specific number of args. This is used to identify the demand in the system.",
    )
    force_return_length: int | None = strawberry.field(
        default=None,
        description="Require that the action has a specific number of returns. This is used to identify the demand in the system.",
    )


class StateDemandModel(BaseModel):
    key: str
    hash: Optional[str] = None
    matches: Optional[list[rmodels.PortMatchModel]] = None
    protocols: Optional[list[str]] = None


@pydantic.type(StateDemandModel, description="The input for creating a action demand.")
class StateDemand:
    key: str = strawberry.field(
        description="The key of the action demand. This is used to identify the action in the system.",
    )
    hash: rscalars.ActionHash | None = strawberry.field(
        default=None,
        description="The hash of the state.",
    )
    matches: list[rtypes.PortMatch] | None = strawberry.field(
        default=None,
        description="The demands for the action args and returns. This is used to identify the demand in the system.",
    )
    protocols: list[strawberry.ID] | None = strawberry.field(
        default=None,
        description="The protocols that the action has to implement. This is used to identify the demand in the system.",
    )


@strawberry_django.type(models.Blok)
class Blok:
    id: strawberry.ID
    name: str
    description: str | None
    creator: User
    url: str
    materialized_bloks: list["MaterializedBlok"] = strawberry_django.field(
        description="Materialized bloks that are instances of this blok.",
    )

    @strawberry_django.field(
        description="Get the actions that this blok can run.",
    )
    def action_demands(self) -> list[ActionDemand]:
        return [ActionDemandModel(**action) for action in self.action_demands]

    @strawberry_django.field(
        description="Get the actions that this blok can run.",
    )
    def state_demands(self) -> list[StateDemand]:
        return [StateDemandModel(**action) for action in self.state_demands]

    @strawberry_django.field(
        description="Get the agents that this blok can be implemented against.",
    )
    def possible_agents(self) -> list[Agent]:
        from facade import managers
        from facade.inputs import ActionDemandInputModel, SchemaDemandInputModel

        queryset = models.Agent.objects

        filtered_ids: set[str] = set()

        if self.action_demands:
            for ports_demand in self.action_demands:
                new_ids = managers.get_action_ids_by_action_demand(
                    action_demand=ActionDemandInputModel(**ports_demand),
                )

                if len(new_ids) == 0:
                    # There are no actions that match the demand
                    raise ValueError(f"No actions found that match the given action demands {ports_demand}")

                for new_id in new_ids:
                    if new_id not in filtered_ids:
                        filtered_ids.add(new_id)

            queryset = queryset.filter(implementations__action__id__in=filtered_ids)

        filtered_ids: set[str] = set()
        if self.state_demands:
            for state_demand in self.state_demands:
                fitting_schema_ids = managers.get_state_ids_by_demands(
                    SchemaDemandInputModel(
                        **state_demand,
                    ).matches,
                    model="facade_stateschema",
                )

                if len(fitting_schema_ids) == 0:
                    return queryset.none()

                for new_id in fitting_schema_ids:
                    if new_id not in filtered_ids:
                        filtered_ids.add(new_id)

            queryset = queryset.filter(states__state_schema__id__in=list(filtered_ids))

        return queryset.distinct()


@strawberry_django.type(models.MaterializedBlok)
class MaterializedBlok:
    id: strawberry.ID
    dashboard: Dashboard
    blok: Blok
    agent: Agent
    name: str | None
    description: str | None
    created_at: datetime.datetime
    updated_at: datetime.datetime
    state_mappings: list["StateMapping"] = strawberry_django.field(
        description="Mappings of states to this materialized blok.",
    )
    action_mappings: list["ActionMapping"] = strawberry_django.field(
        description="Mappings of actions to this materialized blok.",
    )


@strawberry_django.type(models.StateSchema)
class StateSchema:
    id: strawberry.ID
    hash: str
    name: str

    @strawberry_django.field()
    def ports(self) -> list[rtypes.Port]:
        return [rmodels.PortModel(**i) for i in self.ports]


@strawberry_django.type(models.State)
class State:
    id: strawberry.ID
    state_schema: StateSchema = strawberry_django.field(deprecation_reason="Use schema instead")

    value: scalars.Args
    agent: Agent
    interface: str
    created_at: datetime.datetime
    updated_at: datetime.datetime
    historical_states: list["HistoricalState"]

    @strawberry_django.field(deprecation_reason="Use schema instead")
    def schema(self) -> StateSchema:
        return self.state_schema


@strawberry_django.type(models.HistoricalState)
class HistoricalState:
    id: strawberry.ID
    state: State
    value: scalars.Args
    archived_at: datetime.datetime


@strawberry.type
class JSONPatch:
    op: enums.JSONPatchOperation
    path: str
    value: scalars.Args


@strawberry.type
class StateUpdateEvent:
    state_id: str
    patches: list[JSONPatch]


@strawberry_django.type(models.ActionMapping)
class ActionMapping:
    id: strawberry.ID
    key: str
    implementation: Implementation
    materialized_blok: MaterializedBlok
    created_at: datetime.datetime
    updated_at: datetime.datetime


@strawberry_django.type(models.StateMapping)
class StateMapping:
    id: strawberry.ID
    key: str
    implementation: Implementation
    state: State
    crreated_at: datetime.datetime
    updated_at: datetime.datetime


@strawberry_django.type(models.StructurePackage, filters=filters.StructurePackageFilter, pagination=True, description="A package of structures.")
class StructurePackage:
    id: strawberry.ID
    key: str
    description: str | None
    version: str
    structures: list["Structure"] = strawberry_django.field(
        description="Structures that are part of this package.",
    )
    interfaces: list["Interface"] = strawberry_django.field(
        description="Interfaces that are part of this package.",
    )


@strawberry_django.type(models.Interface, filters=filters.InterfaceFilter, pagination=True, description="If this structure is the default in its package.")
class Interface:
    id: strawberry.ID
    key: str
    description: str | None
    package: StructurePackage
    implementations: list[Implementation] = strawberry_django.field(description="Implementations that implement this interface.")
    output_usages: list["OutputInterfaceUsage"] = strawberry_django.field(
        description="Usages of this interface as an output in actions.",
    )
    input_usages: list["InputInterfaceUsage"] = strawberry_django.field(
        description="Usages of this interface as an input in actions.",
    )


@strawberry_django.type(models.Structure, filters=filters.StructureFilter, pagination=True, description="A strucssture representing a data schema or type.")
class Structure:
    id: strawberry.ID
    key: strawberry.ID
    package: StructurePackage
    description: str | None
    implements: list[Interface] = strawberry_django.field(
        description="Interfaces that this structure implements.",
    )
    output_usages: list["OutputStructureUsage"] = strawberry_django.field(
        description="Usages of this structure as an output in actions.",
    )
    input_usages: list["InputStructureUsage"] = strawberry_django.field(
        description="Usages of this structure as an input in actions.",
    )

    @strawberry_django.field(description="The object ID that this structure represents.")
    def identifier(self) -> strawberry.ID:
        return f"@{self.package.key}/{self.key}"

    @strawberry_django.field(description="Get the query to retrieve data for this structure.")
    def get_query(self) -> str | None:
        return self.get_query

    @strawberry_django.field(description="Get the query to describe the schema of this structure.")
    def describe_query(self) -> str | None:
        return self.describe_query


@strawberry_django.type(models.InputStructureUsage, filters=filters.InputStructureUsageFilter, pagination=True, description="Usage of an input structure in an action.")
class InputStructureUsage:
    id: strawberry.ID
    structure: Structure
    action: Action
    port_index: int
    port_key: str
    modifiers: list[str]


@strawberry_django.type(models.OutputStructureUsage, filters=filters.OutputStructureUsageFilter, pagination=True, description="Usage of an output structure in an action.")
class OutputStructureUsage:
    id: strawberry.ID
    structure: Structure
    action: Action
    port_index: int
    port_key: str
    modifiers: list[str]


@strawberry_django.type(models.InputInterfaceUsage, filters=filters.InputInterfaceUsageFilter, pagination=True, description="Usage of an input interface in an action.")
class InputInterfaceUsage:
    id: strawberry.ID
    interface: Interface
    action: Action
    port_index: int
    port_key: str
    modifiers: list[str]


@strawberry_django.type(models.OutputInterfaceUsage, filters=filters.OutputInterfaceUsageFilter, pagination=True, description="Usage of an output interface in an action.")
class OutputInterfaceUsage:
    id: strawberry.ID
    interface: Interface
    action: Action
    port_index: int
    port_key: str
    modifiers: list[str]
