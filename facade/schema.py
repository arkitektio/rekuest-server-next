from kante.types import Info
from typing import AsyncGenerator
import strawberry
from strawberry_django.optimizer import DjangoOptimizerExtension

from strawberry import ID
from kante.directives import upper, replace, relation
from strawberry.permission import BasePermission
from typing import Any, Type
from facade import types, models, mutations, subscriptions, scalars, queries
from strawberry.field_extensions import InputMutationExtension
import strawberry_django
from reaktion.graphql import queries as reaktion_queries
from reaktion.graphql import mutations as reaktion_mutations
from reaktion import types as reaktion_types
from koherent.strawberry.extension import KoherentExtension
from authentikate.strawberry.permissions import IsAuthenticated


@strawberry.type
class Query:
    nodes: list[types.Node] = strawberry_django.field()
    templates: list[types.Template] = strawberry_django.field()
    assignations: list[types.Assignation] = strawberry_django.field()
    test_results: list[types.TestResult] = strawberry_django.field()
    test_cases: list[types.TestCase] = strawberry_django.field()
    reservations: list[types.Reservation] = strawberry_django.field()
    provisions: list[types.Provision] = strawberry_django.field()
    node = strawberry_django.field(resolver=queries.node)
    flow = strawberry_django.field(resolver=reaktion_queries.flow)
    flows: list[reaktion_types.Flow] = strawberry_django.field()
    workspaces: list[reaktion_types.Workspace] = strawberry_django.field()
    workspace = strawberry_django.field(resolver=reaktion_queries.workspace)
    reactive_templates: list[
        reaktion_types.ReactiveTemplate
    ] = strawberry_django.field()
    reactive_template = strawberry_django.field(
        resolver=reaktion_queries.reactive_template
    )

    @strawberry_django.field()
    def agent(self, info: Info, id: strawberry.ID) -> types.Agent:
        print("hallo")
        return models.Agent.objects.get(id=id)

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
    def provision(self, info: Info, id: strawberry.ID) -> types.Provision:
        return models.Provision.objects.get(id=id)

    @strawberry_django.field()
    def assignation(self, info: Info, id: strawberry.ID) -> types.Assignation:
        return models.Assignation.objects.get(id=id)


@strawberry.type
class Mutation:
    create_template: types.Template = strawberry_django.mutation(
        resolver=mutations.create_template
    )
    ack: types.Assignation = strawberry_django.mutation(resolver=mutations.ack)
    assign: types.Assignation = strawberry_django.mutation(resolver=mutations.assign)
    unassign: types.Assignation = strawberry_django.mutation(
        resolver=mutations.unassign
    )
    reserve: types.Reservation = strawberry_django.mutation(resolver=mutations.reserve)
    unreserve: types.Reservation = strawberry_django.mutation(
        resolver=mutations.unreserve
    )
    create_test_case: types.TestCase = strawberry_django.mutation(
        resolver=mutations.create_test_case
    )

    create_test_result: types.TestResult = strawberry_django.mutation(
        resolver=mutations.create_test_result
    )
    update_workspace = strawberry_django.mutation(
        resolver=reaktion_mutations.update_workspace
    )
    create_workspace = strawberry_django.mutation(
        permission_classes=[IsAuthenticated],
        resolver=reaktion_mutations.create_workspace,
    )


@strawberry.type
class Subscription:
    new_nodes = strawberry.subscription(resolver=subscriptions.new_nodes)
    assignations = strawberry.subscription(resolver=subscriptions.assignations)
    reservations = strawberry.subscription(resolver=subscriptions.reservations)
    provisions = strawberry.subscription(resolver=subscriptions.provisions)


schema = strawberry.Schema(
    query=Query,
    subscription=Subscription,
    mutation=Mutation,
    directives=[upper, replace, relation],
    extensions=[
        DjangoOptimizerExtension,
        KoherentExtension,
    ],
    types=[
        types.SliderAssignWidget,
        types.ChoiceAssignWidget,
        types.SearchAssignWidget,
        types.CustomReturnWidget,
        types.ChoiceReturnWidget,
        types.StringAssignWidget,
        types.CustomAssignWidget,
        types.CustomEffect,
        types.MessageEffect,
        reaktion_types.ArkitektGraphNode,
        reaktion_types.RetriableNode,
        reaktion_types.ArgNode,
        reaktion_types.ReturnNode,
        reaktion_types.VanillaEdge,
        reaktion_types.LoggingEdge,
        reaktion_types.ReactiveNode,
    ]  # We really need to register
    # all the types here, otherwise the schema will not be able to resolve them
    # and will throw a cryptic error
)
