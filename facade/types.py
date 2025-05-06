import datetime
from typing import Optional

import strawberry
import strawberry_django
from authentikate.models import Client, User
from django.conf import settings
from django.utils import timezone
from facade import enums, filters, models, scalars
from rekuest_core import enums as renums
from rekuest_core import scalars as rscalars
from rekuest_core.objects import models as rmodels
from rekuest_core.objects import types as rtypes
from strawberry import LazyType
from kante.types import Info
from rekuest_ui_core.objects import models as uimodels
from rekuest_ui_core.objects import types as uitypes


@strawberry_django.type(User, filters=filters.UserFilter, pagination=True, order=filters.UserOrder, description="Represents an authenticated user.")
class User:
    sub: strawberry.ID = strawberry_django.field(description="The subject identifier of the user.")


@strawberry_django.type(Client, filters=filters.ClientFilter, pagination=True, order=filters.ClientOrder, description="Represents a registered OAuth2 client.")
class Client:
    id: strawberry.ID = strawberry_django.field(description="Unique ID of the client.")
    name: str = strawberry_django.field(description="Name of the client.")
    client_id: str = strawberry_django.field(description="OAuth2 client ID.")


@strawberry_django.type(models.Registry, description="Links a user and a client for registry tracking.")
class Registry:
    id: strawberry.ID = strawberry_django.field(description="Unique identifier for the registry.")
    client: Client = strawberry_django.field(description="The associated client.")
    user: User = strawberry_django.field(description="The associated user.")
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

    @strawberry_django.field(description="Retrieve assignations where this action has run.")
    def runs(self) -> list[LazyType["Assignation", __name__]] | None:
        return models.Assignation.objects.filter(provision__implementation__action=self).order_by("-created_at")

    @strawberry_django.field(description="Input arguments (ports) for the action.")
    def args(self) -> list[rtypes.Port]:
        return [rmodels.PortModel(**i) for i in self.args]

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


@strawberry_django.type(models.Dependency, filters=filters.DependencyFilter, pagination=True, description="Represents a dependency between implementations and actions.")
class Dependency:
    id: strawberry.ID = strawberry_django.field(description="Unique ID of the dependency.")
    implementation: "Implementation" = strawberry_django.field(description="Implementation this dependency belongs to.")
    action: Action | None = strawberry_django.field(description="Optional action this dependency refers to.")
    hash: rscalars.ActionHash = strawberry_django.field(description="Current hash of the dependency.")
    initial_hash: rscalars.ActionHash = strawberry_django.field(description="Original hash when the dependency was created.")
    reference: str | None = strawberry_django.field(description="Optional string identifier or tag for reference.")
    optional: bool = strawberry_django.field(description="Indicates if the dependency is optional.")

    @strawberry_django.field(description="Binds information attached to the dependency.")
    def binds(self) -> rtypes.Binds | None:
        return rmodels.BindsModel(**self.binds) if self.binds else None

    @strawberry_django.field(description="Check if this dependency can be resolved by a connected agent.")
    def resolvable(self, info: Info) -> bool:
        qs = models.Implementation.objects.filter(
            action__hash=self.initial_hash,
            agent__connected=True,
        )
        return qs.exists()


@strawberry_django.type(models.Implementation, filters=filters.ImplementationFilter, pagination=True, description="Represents a concrete implementation of an action.")
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
    instance_id: scalars.InstanceID = strawberry_django.field(description="Unique instance identifier on the agent.")
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


# Completion of type and field descriptions for remaining types like Waiter, Reservation, Assignation, and more


@strawberry_django.type(models.Waiter, filters=filters.WaiterFilter, pagination=True, description="Entity that waits for the completion of assignations.")
class Waiter:
    id: strawberry.ID = strawberry_django.field(description="Unique ID of the waiter.")
    instance_id: scalars.InstanceID = strawberry_django.field(description="Instance ID associated with the waiter.")
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


@strawberry_django.type(models.Assignation, filters=filters.AssignationFilter, pagination=True, description="Tracks the assignment of an implementation to a specific task.")
class Assignation:
    id: strawberry.ID = strawberry_django.field(description="Unique ID of the assignation.")
    reference: str | None = strawberry_django.field(description="Optional external reference for tracking.")
    is_done: bool = strawberry_django.field(description="Indicates if the assignation is completed.")
    args: rscalars.AnyDefault = strawberry_django.field(description="Arguments used in the assignation.")
    root: Optional["Assignation"] = strawberry.field(description="Root assignation in the creation chain.")
    parent: Optional["Assignation"] = strawberry.field(description="Parent assignation that triggered this one.")
    reservation: Optional["Reservation"] = strawberry.field(description="Reservation that caused this assignation.")
    action: "Action" = strawberry.field(description="Action assigned.")
    implementation: "Implementation" = strawberry.field(description="Implementation assigned to execute.")
    latest_event_kind: enums.AssignationEventKind = strawberry.field(description="Type of the latest event.")
    latest_instruct_kind: enums.AssignationInstructKind = strawberry.field(description="Last instruction type.")
    status_message: str | None = strawberry_django.field(description="Current status message.")
    waiter: "Waiter" = strawberry.field(description="Waiter responsible for this assignation.")
    created_at: datetime.datetime = strawberry_django.field(description="Creation timestamp.")
    updated_at: datetime.datetime = strawberry_django.field(description="Last update timestamp.")
    ephemeral: bool = strawberry.field(description="Indicates if the assignation should be deleted after completion.")

    @strawberry_django.field(description="List of recent events for this assignation.")
    def events(self) -> list["AssignationEvent"]:
        return self.events.order_by("created_at")[:10]

    @strawberry_django.field(description="List of recent instructions for this assignation.")
    def instructs(self) -> list["AssignationInstruct"]:
        return self.instructs.order_by("created_at")[:10]

    @strawberry_django.field(description="Get a specific argument by key.")
    def arg(self, key: str) -> scalars.Args | None:
        return self.args.get(key, None)


# Final types: AssignationEvent, Instruct, AgentEvent, TestCase, TestResult, State


@strawberry_django.type(models.AssignationEvent, filters=filters.AssignationEventFilter, pagination=True, description="An event that occurred during an assignation.")
class AssignationEvent:
    id: strawberry.ID = strawberry_django.field(description="Unique ID of the event.")
    name: str = strawberry_django.field(description="Name of the event.")
    returns: rscalars.AnyDefault | None = strawberry_django.field(description="Optional return values.")
    assignation: "Assignation" = strawberry_django.field(description="Associated assignation.")
    kind: enums.AssignationEventKind = strawberry_django.field(description="Kind of assignation event.")
    message: str | None = strawberry_django.field(description="Optional message associated with the event.")
    progress: int | None = strawberry_django.field(description="Progress percentage.")
    created_at: strawberry.auto = strawberry_django.field(description="Time when event was created.")

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


@strawberry_django.type(models.Structure)
class Structure:
    identifier: strawberry.ID
    object: strawberry.ID


@strawberry_django.type(models.Dashboard)
class Dashboard:
    id: strawberry.ID
    name: str | None
    panels: list["Panel"] | None

    @strawberry_django.field()
    def ui_tree(self) -> uitypes.UITree | None:
        model = uimodels.UITreeModel(**self.ui_tree) if self.ui_tree else None
        return model


@strawberry_django.type(models.Panel)
class Panel:
    id: strawberry.ID
    kind: enums.PanelKind
    name: str
    reservation: Reservation | None
    state: Optional["State"]
    accessors: list[str] | None
    submit_on_load: bool
    submit_on_change: bool


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
    state_schema: StateSchema
    value: scalars.Args
    agent: Agent
    created_at: datetime.datetime
    updated_at: datetime.datetime
    historical_states: list["HistoricalState"]


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
