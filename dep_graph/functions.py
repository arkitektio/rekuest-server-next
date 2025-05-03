from typing import List
from facade import models
from .models import (
    ActionActionModel,
    InvalidActionModel,
    ImplementationActionModel,
    DependencyEdgeModel,
    DependencyGraphModel,
    ActionModel,
    ImplementationEdgeModel,
    EdgeModel,
)
from uuid import uuid4


def build_graph_recursive(
    implementation: models.Implementation,
    edges: list[EdgeModel],
    actions: list[ActionModel],
    connect_to=[],
) -> None:
    try:
        provision = implementation.provision
    except Exception as e:
        provision = None

    implementation_action = ImplementationActionModel(
        id=implementation.id,
        implementation_id=implementation.id,
        interface=implementation.interface,
        client_id=implementation.agent.registry.app.client_id,
    )

    actions.append(implementation_action)

    for dep in implementation.dependencies.all():
        if dep.action is not None:
            action = ActionActionModel(action_id=dep.action.id, name=dep.action.name)

            for action_implementation in dep.action.implementations.all():
                build_graph_recursive(
                    action_implementation, edges, actions, connect_to=[action.id]
                )

        else:
            action = InvalidActionModel(initial_hash=dep.initial_hash)

        dep_edge = DependencyEdgeModel(
            source=implementation_action.id,
            target=action.id,
            optional=dep.optional,
            dep_id=dep.id,
        )

        actions.append(action)
        edges.append(dep_edge)

    for i in connect_to:
        edges.append(
            ImplementationEdgeModel(
                source=i, target=implementation_action.id, optional=False
            )
        )


def build_implementation_graph(
    implementation: models.Implementation,
) -> DependencyGraphModel:
    actions = []
    edges = []
    build_graph_recursive(implementation, edges, actions)
    return DependencyGraphModel(actions=actions, edges=edges)


def build_action_graph(action: models.Action) -> DependencyGraphModel:
    actions = []
    edges = []

    action_action = ActionActionModel(action_id=action.id, name=action.name)
    actions.append(action_action)

    for implementation in action.implementations.all():
        build_graph_recursive(
            implementation, edges, actions, connect_to=[action_action.id]
        )
    return DependencyGraphModel(actions=actions, edges=edges)


def build_reservation_graph_recursive(
    reservation: models.Reservation,
    edges: list[EdgeModel],
    actions: list[ActionModel],
    connect_to=[],
) -> None:
    action_action = ActionActionModel(
        action_id=reservation.action.id,
        name=reservation.action.name,
        reservation_id=reservation.id,
        status=reservation.status,
    )
    actions.append(action_action)

    for temp in reservation.action.implementations.all():
        linked = reservation.provisions.filter(implementation=temp).exists()
        provision = temp.provision

        implementation_action = ImplementationActionModel(
            id=temp.id,
            implementation_id=temp.id,
            interface=temp.interface,
            provision_id=provision.id,
            client_id=temp.agent.registry.app.client_id,
            linked=linked,
            reservation_id=reservation.id,
            status=provision.status,
            active=provision.active,
        )
        actions.append(implementation_action)
        edges.append(
            ImplementationEdgeModel(
                source=action_action.id,
                target=implementation_action.id,
                optional=False,
                linked=linked,
            )
        )

        if linked:
            for reservation in provision.caused_reservations.all():
                build_reservation_graph_recursive(
                    reservation, edges, actions, connect_to=[implementation_action.id]
                )

    for i in connect_to:
        edges.append(
            DependencyEdgeModel(source=i, target=action_action.id, optional=False)
        )


def build_reservation_graph(reservation: models.Reservation) -> DependencyGraphModel:
    actions = []
    edges = []

    build_reservation_graph_recursive(reservation, edges, actions)

    return DependencyGraphModel(actions=actions, edges=edges)
