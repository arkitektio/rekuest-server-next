import strawberry
import strawberry_django
from facade import models, mutations, queries, subscriptions, types
from kante.types import Info
from rekuest_core.constants import interface_types
from rekuest_ui_core.constants import interface_types as uiinterface_types
from strawberry_django.optimizer import DjangoOptimizerExtension
from authentikate.strawberry import AuthentikateExtension, AuthExtension, AuthSubscribeExtension
from typing import cast


def field(permission_classes=None, **kwargs):
    "A wrapper for field that adds default permission classes and extensions."
    if permission_classes:
        pass
    else:
        permission_classes = []
    return strawberry_django.field(extensions=[AuthExtension()], **kwargs)


def mutation(**kwargs):
    """A wrapper for mutation that adds default permission classes and extensions."""

    return strawberry_django.mutation(extensions=[AuthExtension()], **kwargs)


def subscription(**kwargs) -> strawberry.subscription:
    """A wrapper for subscription that adds default permission classes and extensions."""
    return strawberry.subscription(extensions=[AuthSubscribeExtension()], **kwargs)


@strawberry.type(description="Root query type for fetching entities in the system.")
class Query:
    clients: list[types.Client] = field(description="List all registered clients.")
    hardware_records: list[types.HardwareRecord] = field(description="List of all hardware records.")
    agents: list[types.Agent] = field(description="Retrieve all compute agents.")
    actions: list[types.Action] = field(description="List of all available actions.")
    protocols: list[types.Protocol] = field(description="Retrieve protocols grouping actions.")
    implementations: list[types.Implementation] = field(description="All registered implementations.")
    test_results: list[types.TestResult] = field(description="Test results associated with test cases.")
    test_cases: list[types.TestCase] = field(description="All test cases.")
    reservations: list[types.Reservation] = field(resolver=queries.reservations, description="List of all reservations.")
    myreservations: list[types.Reservation] = field(resolver=queries.myreservations, description="Reservations made by the current user.")
    shortcuts: list[types.Shortcut] = field(description="List of shortcuts.")
    toolboxes: list[types.Toolbox] = field(description="List of toolboxes containing shortcuts.")
    action = field(resolver=queries.action, description="Fetch a specific action.")
    assignations = field(resolver=queries.assignations, description="Fetch assignations.")
    event = field(resolver=queries.event, description="Fetch a specific event.")
    implementation_at = field(resolver=queries.implementation_at, description="Find implementation at given interface.")
    my_implementation_at = field(resolver=queries.my_implementation_at, description="Find your implementation at a specific interface.")
    dashboards: list[types.Dashboard] = field(description="All dashboards.")
    states: list[types.State] = field(description="All states from agents.")
    bloks: list[types.Blok] = field(description="List of UI Blok.")
    materialized_bloks: list[types.MaterializedBlok] = field(description="List of UI Blok.")
    state_schemas: list[types.StateSchema] = field(description="Available state schemas.")
    memory_shelves: list[types.MemoryShelve] = field(description="All memory shelves.")
    memory_drawers: list[types.MemoryDrawer] = field(description="All memory drawers.")
    structures: list[types.Structure] = field(description="All registered structures.")
    structure_packages: list[types.StructurePackage] = field(description="All registered structure packages.")
    interfaces: list[types.Interface] = field(description="All registered interfaces.")
    tasks: list[types.Assignation] = field(description="All tasks.")

    # Stats
    actionStats: types.ActionStats = field(resolver=types.ActionStatsResolver, description="Statistics about actions and their implementations.")
    assignationStats: types.AssignationStats = field(resolver=types.AssignationStatsResolver, description="Statistics about assignations and their states.")

    state_for = field(resolver=queries.state_for, description="Retrieve state for a specific context.")

    @field(description="Get a specific state by ID.")
    def state(self, info: Info, id: strawberry.ID) -> types.State:
        return cast(types.State, models.State.objects.get(id=id))

    @field(description="Fetch a client by ID.")
    def structure_package(self, info: Info, id: strawberry.ID) -> types.StructurePackage:
        return cast(types.StructurePackage, models.StructurePackage.objects.get(id=id))

    @field(description="Fetch an interface by ID.")
    def interface(self, info: Info, id: strawberry.ID) -> types.Interface:
        return cast(types.Interface, models.Interface.objects.get(id=id))

    @field(description="Fetch a structure by ID.")
    def structure(self, info: Info, id: strawberry.ID) -> types.Structure:
        return cast(types.Structure, models.Structure.objects.get(id=id))

    @field(description="Fetch a memory shelve by ID.")
    def memory_shelve(self, info: Info, id: strawberry.ID) -> types.MemoryShelve:
        return cast(types.MemoryShelve, models.MemoryShelve.objects.get(id=id))

    @field(description="Get a blok by ID.")
    def blok(self, info: Info, id: strawberry.ID) -> types.Blok:
        return cast(types.Blok, models.Blok.objects.get(id=id))

    @field(description="Get a materialized blok by ID.")
    def materialized_blok(self, info: Info, id: strawberry.ID) -> types.MaterializedBlok:
        return cast(types.MaterializedBlok, models.MaterializedBlok.objects.get(id=id))

    @field(description="Retrieve a state schema by ID.")
    def state_schema(self, info: Info, id: strawberry.ID) -> types.StateSchema:
        return cast(types.StateSchema, models.StateSchema.objects.get(id=id))

    @field(description="Get toolbox by ID.")
    def toolbox(self, info: Info, id: strawberry.ID) -> types.Toolbox:
        return cast(types.Toolbox, models.Toolbox.objects.get(id=id))

    @field(description="Retrieve shortcut by ID.")
    def shortcut(self, info: Info, id: strawberry.ID) -> types.Shortcut:
        return cast(types.Shortcut, models.Shortcut.objects.get(id=id))

    @field(description="Get hardware record by ID.")
    def hardware_record(self, info: Info, id: strawberry.ID) -> types.HardwareRecord:
        return cast(types.HardwareRecord, models.HardwareRecord.objects.get(id=id))

    @field(description="Retrieve an agent by ID.")
    def agent(self, info: Info, id: strawberry.ID) -> types.Agent:
        return cast(types.Agent, models.Agent.objects.get(id=id))

    @field(description="Get dashboard by ID.")
    def dashboard(self, info: Info, id: strawberry.ID) -> types.Dashboard:
        return cast(types.Dashboard, models.Dashboard.objects.get(id=id))

    @field(description="Fetch a dependency by ID.")
    def dependency(self, info: Info, id: strawberry.ID) -> types.Dependency:
        return cast(types.Dependency, models.Dependency.objects.get(id=id))

    @field(description="Retrieve test case by ID.")
    def test_case(self, info: Info, id: strawberry.ID) -> types.TestCase:
        return cast(types.TestCase, models.TestCase.objects.get(id=id))

    @field(description="Get test result by ID.")
    def test_result(self, info: Info, id: strawberry.ID) -> types.TestResult:
        return cast(types.TestResult, models.TestResult.objects.get(id=id))

    @field(description="Retrieve reservation by ID.")
    def reservation(self, info: Info, id: strawberry.ID) -> types.Reservation:
        return cast(types.Reservation, models.Reservation.objects.get(id=id))

    @field(description="Get implementation by ID.")
    def implementation(self, info: Info, id: strawberry.ID) -> types.Implementation:
        return cast(types.Implementation, models.Implementation.objects.get(id=id))

    @field(description="Fetch assignation by ID.")
    def assignation(self, info: Info, id: strawberry.ID) -> types.Assignation:
        return cast(types.Assignation, models.Assignation.objects.get(id=id))


@strawberry.type(description="Root mutation type for executing write operations on the API.")
class Mutation:
    create_implementation = mutation(resolver=mutations.create_implementation, description="Create a new implementation entry.")
    create_foreign_implementation = mutation(resolver=mutations.create_foreign_implementation, description="Register an external implementation.")
    set_extension_implementations = mutation(resolver=mutations.set_extension_implementations, description="Set implementations provided by an extension.")
    ack = mutation(resolver=mutations.ack, description="Acknowledge an assignation.")
    bounce = mutation(resolver=mutations.bounce, description="Bounce an agent so it reconnects.")
    kick = mutation(resolver=mutations.kick, description="Kick an agent to force disconnect. It will fail and not reconnect.")
    assign = mutation(resolver=mutations.assign, description="Assign a task to an agent.")
    cancel = mutation(resolver=mutations.cancel, description="Cancel an active assignation.")
    step = mutation(resolver=mutations.step, description="Advance an assignation one step.")
    pause = mutation(resolver=mutations.pause, description="Pause an ongoing assignation.")
    resume = mutation(resolver=mutations.resume, description="Resume a paused assignation.")
    collect = mutation(resolver=mutations.collect, description="Collect results from an assignation.")
    interrupt = mutation(resolver=mutations.interrupt, description="Interrupt the execution of an assignation.")
    reinit = mutation(resolver=mutations.reinit, description="Reinitialize the assignation or agent.")
    block = mutation(resolver=mutations.block, description="Block an agent from connecting.")
    unblock = mutation(resolver=mutations.unblock, description="Unblock a previously blocked agent.")
    reserve = mutation(resolver=mutations.reserve, description="Reserve an implementation for future use.")
    unreserve = mutation(resolver=mutations.unreserve, description="Release a reserved implementation.")
    delete_implementation = mutation(resolver=mutations.delete_implementation, description="Delete a registered implementation.")
    ensure_agent = mutation(resolver=mutations.ensure_agent, description="Ensure agent record exists or is up to date.")
    create_test_case = mutation(resolver=mutations.create_test_case, description="Create a new test case.")
    create_test_result = mutation(resolver=mutations.create_test_result, description="Create a test result record.")
    shelve_in_memory_drawer = mutation(resolver=mutations.shelve_in_memory_drawer, description="Shelve data into a memory drawer.")
    unshelve_memory_drawer = mutation(resolver=mutations.unshelve_memory_drawer, description="Unshelve data from a memory drawer.")
    create_dashboard = mutation(resolver=mutations.create_dashboard, description="Create a dashboard layout.")
    create_state_schema = mutation(resolver=mutations.create_state_schema, description="Define a new state schema.")
    create_blok = mutation(resolver=mutations.create_blok, description="Create a user interface panel.")
    set_state = mutation(resolver=mutations.set_state, description="Set the value of a state object.")
    materialize_blok = mutation(resolver=mutations.materialize_blok, description="Materialize a UI blok into a concrete instance on a dashboard.")
    update_state = mutation(resolver=mutations.update_state, description="Update fields in a state object.")
    archive_state = mutation(resolver=mutations.archive_state, description="Archive a state schema.")
    pin_agent = mutation(resolver=mutations.pin_agent, description="Pin an agent to the user.")
    pin_implementation = mutation(resolver=mutations.pin_implementation, description="Pin an implementation to the user.")
    delete_agent = mutation(resolver=mutations.delete_agent, description="Delete an agent record.")
    create_shortcut = mutation(resolver=mutations.create_shortcut, description="Create a shortcut to an action.")
    delete_shortcut = mutation(resolver=mutations.delete_shortcut, description="Delete a shortcut.")
    create_toolbox = mutation(resolver=mutations.create_toolbox, description="Create a new toolbox with shortcuts.")
    set_agent_states = mutation(resolver=mutations.set_agent_states, description="Set states for an agent.")
    cleanup_actions = mutation(resolver=mutations.cleanup_actions, description="Delete unreferenced actions from the system.")


@strawberry.type(description="Root subscription type for real-time event streams from the system.")
class Subscription:
    new_actions = subscription(resolver=subscriptions.new_actions, description="Subscribe to notifications when new actions are created.")
    assignations = subscription(resolver=subscriptions.assignations, description="Subscribe to updates on assignations.")
    reservations = subscription(resolver=subscriptions.reservations, description="Subscribe to updates on reservations.")
    assignation_events = subscription(resolver=subscriptions.assignation_events, description="Subscribe to events related to assignations.")
    agents = subscription(resolver=subscriptions.agents, description="Subscribe to updates on agent connections and statuses.")
    implementation_change = subscription(resolver=subscriptions.implementation_change, description="Subscribe to changes in implementations.")
    implementations = subscription(resolver=subscriptions.implementations, description="Subscribe to creation or updates of implementations.")
    state_update_events = subscription(resolver=subscriptions.state_update_events, description="Subscribe to updates of state values and patches.")


schema = strawberry.Schema(
    query=Query,
    subscription=Subscription,
    mutation=Mutation,
    extensions=[
        DjangoOptimizerExtension,
        AuthentikateExtension,
    ],
    types=interface_types + uiinterface_types,
    # We really need to register
    # all the types here, otherwise the schema will not be able to resolve them
    # and will throw a cryptic error
)
