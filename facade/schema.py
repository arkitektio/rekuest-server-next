import strawberry
import strawberry_django
from facade import models, mutations, queries, subscriptions, types
from kante.types import Info
from rekuest_core.constants import interface_types
from rekuest_ui_core.constants import interface_types as uiinterface_types
from strawberry_django.optimizer import DjangoOptimizerExtension
from authentikate.strawberry import AuthentikateExtension
from typing import cast

@strawberry.type(description="Root query type for fetching entities in the system.")
class Query:
    clients: list[types.Client] = strawberry_django.field(description="List all registered clients.")
    hardware_records: list[types.HardwareRecord] = strawberry_django.field(description="List of all hardware records.")
    agents: list[types.Agent] = strawberry_django.field(description="Retrieve all compute agents.")
    actions: list[types.Action] = strawberry_django.field(description="List of all available actions.")
    protocols: list[types.Protocol] = strawberry_django.field(description="Retrieve protocols grouping actions.")
    implementations: list[types.Implementation] = strawberry_django.field(description="All registered implementations.")
    test_results: list[types.TestResult] = strawberry_django.field(description="Test results associated with test cases.")
    test_cases: list[types.TestCase] = strawberry_django.field(description="All test cases.")
    reservations: list[types.Reservation] = strawberry_django.field(
        resolver=queries.reservations, description="List of all reservations."
    )
    myreservations: list[types.Reservation] = strawberry_django.field(
        resolver=queries.myreservations, description="Reservations made by the current user."
    )
    shortcuts: list[types.Shortcut] = strawberry_django.field(description="List of shortcuts.")
    toolboxes: list[types.Toolbox] = strawberry_django.field(description="List of toolboxes containing shortcuts.")
    action = strawberry_django.field(resolver=queries.action, description="Fetch a specific action.")
    assignations = strawberry_django.field(resolver=queries.assignations, description="Fetch assignations.")
    event = strawberry_django.field(resolver=queries.event, description="Fetch a specific event.")
    implementation_at = strawberry_django.field(resolver=queries.implementation_at, description="Find implementation at given interface.")
    my_implementation_at = strawberry_django.field(
        resolver=queries.my_implementation_at, description="Find your implementation at a specific interface."
    )
    dashboards: list[types.Dashboard] = strawberry_django.field(description="All dashboards.")
    states: list[types.State] = strawberry_django.field(description="All states from agents.")
    panels: list[types.Panel] = strawberry_django.field(description="List of UI panels.")
    state_schemas: list[types.StateSchema] = strawberry_django.field(description="Available state schemas.")
    memory_shelves: list[types.MemoryShelve] = strawberry_django.field(description="All memory shelves.")
    state_for = strawberry_django.field(resolver=queries.state_for, description="Retrieve state for a specific context.")

    @strawberry_django.field(description="Get a specific state by ID.")
    def state(self, info: Info, id: strawberry.ID) -> types.State:
        return cast(types.State, models.State.objects.get(id=id))

    @strawberry_django.field(description="Fetch a memory shelve by ID.")
    def memory_shelve(self, info: Info, id: strawberry.ID) -> types.MemoryShelve:
        return cast(types.MemoryShelve, models.MemoryShelve.objects.get(id=id))

    @strawberry_django.field(description="Get a panel by ID.")
    def panel(self, info: Info, id: strawberry.ID) -> types.Panel:
        return cast(types.Panel, models.Panel.objects.get(id=id))

    @strawberry_django.field(description="Retrieve a state schema by ID.")
    def state_schema(self, info: Info, id: strawberry.ID) -> types.StateSchema:
        return cast(types.StateSchema, models.StateSchema.objects.get(id=id))

    @strawberry_django.field(description="Get toolbox by ID.")
    def toolbox(self, info: Info, id: strawberry.ID) -> types.Toolbox:
        return cast(types.Toolbox, models.Toolbox.objects.get(id=id))

    @strawberry_django.field(description="Retrieve shortcut by ID.")
    def shortcut(self, info: Info, id: strawberry.ID) -> types.Shortcut:
        return cast(types.Shortcut, models.Shortcut.objects.get(id=id))

    @strawberry_django.field(description="Get hardware record by ID.")
    def hardware_record(self, info: Info, id: strawberry.ID) -> types.HardwareRecord:
        return cast(types.HardwareRecord, models.HardwareRecord.objects.get(id=id))

    @strawberry_django.field(description="Retrieve an agent by ID.")
    def agent(self, info: Info, id: strawberry.ID) -> types.Agent:
        return cast(types.Agent, models.Agent.objects.get(id=id))

    @strawberry_django.field(description="Get dashboard by ID.")
    def dashboard(self, info: Info, id: strawberry.ID) -> types.Dashboard:
        return cast(types.Dashboard, models.Dashboard.objects.get(id=id))

    @strawberry_django.field(description="Fetch a dependency by ID.")
    def dependency(self, info: Info, id: strawberry.ID) -> types.Dependency:
        return cast(types.Dependency, models.Dependency.objects.get(id=id))

    @strawberry_django.field(description="Retrieve test case by ID.")
    def test_case(self, info: Info, id: strawberry.ID) -> types.TestCase:
        return cast(types.TestCase, models.TestCase.objects.get(id=id))

    @strawberry_django.field(description="Get test result by ID.")
    def test_result(self, info: Info, id: strawberry.ID) -> types.TestResult:
        return cast(types.TestResult, models.TestResult.objects.get(id=id))

    @strawberry_django.field(description="Retrieve reservation by ID.")
    def reservation(self, info: Info, id: strawberry.ID) -> types.Reservation:
        return cast(types.Reservation, models.Reservation.objects.get(id=id))

    @strawberry_django.field(description="Get implementation by ID.")
    def implementation(self, info: Info, id: strawberry.ID) -> types.Implementation:
        return cast(types.Implementation, models.Implementation.objects.get(id=id))

    @strawberry_django.field(description="Fetch assignation by ID.")
    def assignation(self, info: Info, id: strawberry.ID) -> types.Assignation:
        return cast(types.Assignation, models.Assignation.objects.get(id=id))

@strawberry.type(description="Root mutation type for executing write operations on the API.")
class Mutation:
    create_implementation = strawberry_django.mutation(
        resolver=mutations.create_implementation,
        description="Create a new implementation entry."
    )
    create_foreign_implementation = strawberry_django.mutation(
        resolver=mutations.create_foreign_implementation,
        description="Register an external implementation."
    )
    set_extension_implementations = strawberry_django.mutation(
        resolver=mutations.set_extension_implementations,
        description="Set implementations provided by an extension."
    )
    ack = strawberry_django.mutation(
        resolver=mutations.ack,
        description="Acknowledge an assignation."
    )
    assign = strawberry_django.mutation(
        resolver=mutations.assign,
        description="Assign a task to an agent."
    )
    cancel = strawberry_django.mutation(
        resolver=mutations.cancel,
        description="Cancel an active assignation."
    )
    step = strawberry_django.mutation(
        resolver=mutations.step,
        description="Advance an assignation one step."
    )
    pause = strawberry_django.mutation(
        resolver=mutations.pause,
        description="Pause an ongoing assignation."
    )
    resume = strawberry_django.mutation(
        resolver=mutations.resume,
        description="Resume a paused assignation."
    )
    collect = strawberry_django.mutation(
        resolver=mutations.collect,
        description="Collect results from an assignation."
    )
    interrupt = strawberry_django.mutation(
        resolver=mutations.interrupt,
        description="Interrupt the execution of an assignation."
    )
    reinit = strawberry_django.mutation(
        resolver=mutations.reinit,
        description="Reinitialize the assignation or agent."
    )
    reserve = strawberry_django.mutation(
        resolver=mutations.reserve,
        description="Reserve an implementation for future use."
    )
    unreserve = strawberry_django.mutation(
        resolver=mutations.unreserve,
        description="Release a reserved implementation."
    )
    delete_implementation = strawberry_django.mutation(
        resolver=mutations.delete_implementation,
        description="Delete a registered implementation."
    )
    ensure_agent = strawberry_django.mutation(
        resolver=mutations.ensure_agent,
        description="Ensure agent record exists or is up to date."
    )
    create_test_case = strawberry_django.mutation(
        resolver=mutations.create_test_case,
        description="Create a new test case."
    )
    create_test_result = strawberry_django.mutation(
        resolver=mutations.create_test_result,
        description="Create a test result record."
    )
    shelve_in_memory_drawer = strawberry_django.mutation(
        resolver=mutations.shelve_in_memory_drawer,
        description="Shelve data into a memory drawer."
    )
    unshelve_memory_drawer = strawberry_django.mutation(
        resolver=mutations.unshelve_memory_drawer,
        description="Unshelve data from a memory drawer."
    )
    create_dashboard = strawberry_django.mutation(
        resolver=mutations.create_dashboard,
        description="Create a dashboard layout."
    )
    create_state_schema = strawberry_django.mutation(
        resolver=mutations.create_state_schema,
        description="Define a new state schema."
    )
    create_panel = strawberry_django.mutation(
        resolver=mutations.create_panel,
        description="Create a user interface panel."
    )
    set_state = strawberry_django.mutation(
        resolver=mutations.set_state,
        description="Set the value of a state object."
    )
    update_state = strawberry_django.mutation(
        resolver=mutations.update_state,
        description="Update fields in a state object."
    )
    archive_state = strawberry_django.mutation(
        resolver=mutations.archive_state,
        description="Archive a state schema."
    )
    pin_agent = strawberry_django.mutation(
        resolver=mutations.pin_agent,
        description="Pin an agent to the user."
    )
    pin_implementation = strawberry_django.mutation(
        resolver=mutations.pin_implementation,
        description="Pin an implementation to the user."
    )
    delete_agent = strawberry_django.mutation(
        resolver=mutations.delete_agent,
        description="Delete an agent record."
    )
    create_shortcut = strawberry_django.mutation(
        resolver=mutations.create_shortcut,
        description="Create a shortcut to an action."
    )
    delete_shortcut = strawberry_django.mutation(
        resolver=mutations.delete_shortcut,
        description="Delete a shortcut."
    )
    create_toolbox = strawberry_django.mutation(
        resolver=mutations.create_toolbox,
        description="Create a new toolbox with shortcuts."
    )



@strawberry.type(description="Root subscription type for real-time event streams from the system.")
class Subscription:
    new_actions = strawberry.subscription(
        resolver=subscriptions.new_actions,
        description="Subscribe to notifications when new actions are created."
    )
    assignations = strawberry.subscription(
        resolver=subscriptions.assignations,
        description="Subscribe to updates on assignations."
    )
    reservations = strawberry.subscription(
        resolver=subscriptions.reservations,
        description="Subscribe to updates on reservations."
    )
    assignation_events = strawberry.subscription(
        resolver=subscriptions.assignation_events,
        description="Subscribe to events related to assignations."
    )
    agents = strawberry.subscription(
        resolver=subscriptions.agents,
        description="Subscribe to updates on agent connections and statuses."
    )
    implementation_change = strawberry.subscription(
        resolver=subscriptions.implementation_change,
        description="Subscribe to changes in implementations."
    )
    implementations = strawberry.subscription(
        resolver=subscriptions.implementations,
        description="Subscribe to creation or updates of implementations."
    )
    state_update_events = strawberry.subscription(
        resolver=subscriptions.state_update_events,
        description="Subscribe to updates of state values and patches."
    )



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
