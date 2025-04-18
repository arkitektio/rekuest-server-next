from typing import Any, AsyncGenerator, Type

import strawberry
import strawberry_django
from authentikate.strawberry.permissions import IsAuthenticated
from facade import models, mutations, queries, scalars, subscriptions, types
from kante.directives import relation, replace, upper
from kante.types import Info
from koherent.strawberry.extension import KoherentExtension
from rekuest_core.constants import interface_types
from rekuest_ui_core.constants import interface_types as uiinterface_types
from strawberry import ID
from strawberry.field_extensions import InputMutationExtension
from strawberry.permission import BasePermission
from strawberry_django.optimizer import DjangoOptimizerExtension


@strawberry.type
class Query:
    clients: list[types.App] = strawberry_django.field()
    hardware_records: list[types.HardwareRecord] = strawberry_django.field()
    agents: list[types.Agent] = strawberry_django.field()
    nodes: list[types.Node] = strawberry_django.field()
    protocols: list[types.Protocol] = strawberry_django.field()
    templates: list[types.Template] = strawberry_django.field()
    test_results: list[types.TestResult] = strawberry_django.field()
    test_cases: list[types.TestCase] = strawberry_django.field()
    reservations: list[types.Reservation] = strawberry_django.field()
    reservations: list[types.Reservation] = strawberry_django.field(
        resolver=queries.reservations
    )
    myreservations: list[types.Reservation] = strawberry_django.field(
        resolver=queries.myreservations
    )
    shortcuts: list[types.Shortcut] = strawberry_django.field()
    toolboxes: list[types.Toolbox] = strawberry_django.field()
    
    
    node = strawberry_django.field(resolver=queries.node)
    assignations = strawberry_django.field(resolver=queries.assignations)
    event = strawberry_django.field(resolver=queries.event)
    template_at = strawberry_django.field(resolver=queries.template_at)
    my_template_at = strawberry_django.field(resolver=queries.my_template_at)
    dashboards: list[types.Dashboard] = strawberry_django.field()
    states: list[types.State] = strawberry_django.field()
    panels: list[types.Panel] = strawberry_django.field()
    state_schemas: list[types.StateSchema] = strawberry_django.field()

    state_for = strawberry_django.field(resolver=queries.state_for)

    @strawberry_django.field()
    def state(self, info: Info, id: strawberry.ID) -> types.State:
        return models.State.objects.get(id=id)

    @strawberry_django.field()
    def panel(self, info: Info, id: strawberry.ID) -> types.Panel:
        return models.Panel.objects.get(id=id)

    @strawberry_django.field()
    def state_schema(self, info: Info, id: strawberry.ID) -> types.StateSchema:
        return models.StateSchema.objects.get(id=id)
    
    @strawberry_django.field()
    def toolbox(self, info: Info, id: strawberry.ID) -> types.Toolbox:
        return models.Toolbox.objects.get(id=id)
    
    @strawberry_django.field()
    def shortcut(self, info: Info, id: strawberry.ID) -> types.Shortcut:
        return models.Shortcut.objects.get(id=id)

    @strawberry_django.field()
    def hardware_record(self, info: Info, id: strawberry.ID) -> types.HardwareRecord:
        return models.HardwareRecord.objects.get(id=id)

    @strawberry_django.field()
    def agent(self, info: Info, id: strawberry.ID) -> types.Agent:
        return models.Agent.objects.get(id=id)

    @strawberry_django.field()
    def dashboard(self, info: Info, id: strawberry.ID) -> types.Dashboard:
        return models.Dashboard.objects.get(id=id)

    @strawberry_django.field()
    def dependency(self, info: Info, id: strawberry.ID) -> types.Dependency:
        return models.Dependency.objects.get(id=id)

    @strawberry_django.field()
    def test_case(self, info: Info, id: strawberry.ID) -> types.TestCase:
        return models.TestCase.objects.get(id=id)

    @strawberry_django.field()
    def test_result(self, info: Info, id: strawberry.ID) -> types.TestResult:
        return models.TestResult.objects.get(id=id)

    @strawberry_django.field()
    def reservation(self, info: Info, id: strawberry.ID) -> types.Reservation:
        return models.Reservation.objects.get(id=id)

    @strawberry_django.field()
    def template(self, info: Info, id: strawberry.ID) -> types.Template:
        return models.Template.objects.get(id=id)

    @strawberry_django.field()
    def assignation(self, info: Info, id: strawberry.ID) -> types.Assignation:
        return models.Assignation.objects.get(id=id)


@strawberry.type
class Mutation:
    create_template: types.Template = strawberry_django.mutation(
        resolver=mutations.create_template
    )
    create_foreign_template: types.Template = strawberry_django.mutation(
        resolver=mutations.create_foreign_template
    )
    set_extension_templates: list[types.Template] = strawberry_django.mutation(
        resolver=mutations.set_extension_templates
    )
    ack: types.Assignation = strawberry_django.mutation(resolver=mutations.ack)
    assign: types.Assignation = strawberry_django.mutation(resolver=mutations.assign)
    cancel: types.Assignation = strawberry_django.mutation(resolver=mutations.cancel)
    step: types.Assignation = strawberry_django.mutation(
        resolver=mutations.step, description="Step a assignation"
    )
    pause: types.Assignation = strawberry_django.mutation(
        resolver=mutations.pause, description="Pause a assignation"
    )
    resume: types.Assignation = strawberry_django.mutation(
        resolver=mutations.resume, description="Resume a assignation"
    )
    collect: types.Assignation = strawberry_django.mutation(
        resolver=mutations.collect, description="Collect data from a assignation"
    )
    
    
    interrupt: types.Assignation = strawberry_django.mutation(
        resolver=mutations.interrupt
    )
    reinit = strawberry_django.mutation(resolver=mutations.reinit)
    reserve: types.Reservation = strawberry_django.mutation(resolver=mutations.reserve)
    unreserve: str = strawberry_django.mutation(resolver=mutations.unreserve)

    delete_template: str = strawberry_django.mutation(
        resolver=mutations.delete_template, description="Delete a template"
    )

    ensure_agent: types.Agent = strawberry_django.mutation(
        resolver=mutations.ensure_agent
    )
    create_test_case: types.TestCase = strawberry_django.mutation(
        resolver=mutations.create_test_case
    )

    create_test_result: types.TestResult = strawberry_django.mutation(
        resolver=mutations.create_test_result
    )


    create_hardware_record: types.HardwareRecord = strawberry_django.mutation(
        resolver=mutations.create_hardware_record
    )

    create_dashboard: types.Dashboard = strawberry_django.mutation(
        resolver=mutations.create_dashboard
    )

    create_state_schema: types.StateSchema = strawberry_django.mutation(
        resolver=mutations.create_state_schema
    )

    create_panel: types.Panel = strawberry_django.mutation(
        resolver=mutations.create_panel
    )

    set_state: types.State = strawberry_django.mutation(resolver=mutations.set_state)

    update_state: types.State = strawberry_django.mutation(
        resolver=mutations.update_state
    )

    archive_state: types.StateSchema = strawberry_django.mutation(
        resolver=mutations.archive_state
    )

    # pins
    pin_agent: types.Agent = strawberry_django.mutation(resolver=mutations.pin_agent)
    pin_template: types.Template = strawberry_django.mutation(
        resolver=mutations.pin_template
    )
    delete_agent = strawberry_django.mutation(resolver=mutations.delete_agent)

    # shortcuts
    create_shortcut: types.Shortcut = strawberry_django.mutation(
        resolver=mutations.create_shortcut
    )
    delete_shortcut: str = strawberry_django.mutation(
        resolver=mutations.delete_shortcut
    )
    
    # toolbox
    create_toolbox: types.Toolbox = strawberry_django.mutation(
        resolver=mutations.create_toolbox
    )

@strawberry.type
class Subscription:
    new_nodes = strawberry.subscription(resolver=subscriptions.new_nodes)
    assignations = strawberry.subscription(resolver=subscriptions.assignations)
    reservations = strawberry.subscription(resolver=subscriptions.reservations)
    assignation_events = strawberry.subscription(
        resolver=subscriptions.assignation_events
    )
    agents = strawberry.subscription(resolver=subscriptions.agents)
    template_change = strawberry.subscription(resolver=subscriptions.template_change)
    templates = strawberry.subscription(resolver=subscriptions.templates)
    state_update_events = strawberry.subscription(
        resolver=subscriptions.state_update_events
    )


schema = strawberry.Schema(
    query=Query,
    subscription=Subscription,
    mutation=Mutation,
    directives=[upper, replace, relation],
    extensions=[
        DjangoOptimizerExtension,
        KoherentExtension,
    ],
    types=interface_types + uiinterface_types,
    # We really need to register
    # all the types here, otherwise the schema will not be able to resolve them
    # and will throw a cryptic error
)
