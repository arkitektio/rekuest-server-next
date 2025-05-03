# Initialiaze django

import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "rekuest.settings")

django.setup()

# Import the models
from facade import models
from pydantic import BaseModel, Field


## Build dependency graph

x = models.Implementation.objects.get(id=8)


class InvalidAction(BaseModel):
    id: int
    initial_hash: str


class ActionAction(BaseModel):
    id: int
    action_id: str


class ImplementationAction(BaseModel):
    id: int
    implementation_id: str


class DependencyEdge(BaseModel):
    id: int
    source: str
    target: str
    optional: bool


Action = ActionAction | InvalidAction | ImplementationAction


class Graph(BaseModel):
    actions: list[Action]
    edges: list[DependencyEdge]


def build_graph_recursive(
    implementation_id: int, edges: list[DependencyEdge], actions: list[Action]
) -> None:
    implementation = models.Implementation.objects.get(id=implementation_id)
    actions.append(
        ImplementationAction(id=implementation.id, implementation_id=implementation.id)
    )

    for dep in implementation.dependencies.all():
        if dep.action is not None:
            actions.append(ActionAction(id=dep.action.id, action_id=dep.action.id))
            edges.append(
                DependencyEdge(
                    id=dep.id,
                    source=dep.action.hash,
                    target=implementation.action.hash,
                    optional=dep.optional,
                )
            )
            for implementation in dep.action.implementations.all():
                build_graph_recursive(implementation.id, edges, actions)

        else:
            actions.append(InvalidAction(id=dep.id, initial_hash=dep.initial_hash))
            edges.append(
                DependencyEdge(
                    id=dep.id,
                    source=dep.initial_hash,
                    target=implementation.action.hash,
                    optional=dep.optional,
                )
            )


def build_graph(implementation_id: int) -> Graph:
    actions = []
    edges = []
    build_graph_recursive(implementation_id, edges, actions)
    return Graph(actions=actions, edges=edges)


x = build_graph(8)
