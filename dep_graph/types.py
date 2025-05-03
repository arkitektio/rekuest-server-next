import datetime
from typing import Optional

import strawberry
import strawberry_django
from pydantic import BaseModel
from strawberry import LazyType
from strawberry.experimental import pydantic


from .models import (
    ActionActionModel,
    InvalidActionModel,
    ImplementationActionModel,
    DependencyEdgeModel,
    DependencyGraphModel,
    ImplementationEdgeModel,
)


@pydantic.type(ActionActionModel)
class ActionAction:
    id: str
    action_id: str
    name: str
    status: str | None
    reservation_id: str | None


@pydantic.type(InvalidActionModel)
class InvalidAction:
    id: str
    initial_hash: str


@pydantic.type(ImplementationActionModel)
class ImplementationAction:
    id: str
    implementation_id: str
    interface: str
    client_id: str
    status: str | None
    provision_id: str | None
    reservation_id: str | None
    linked: bool = False
    active: bool = False


@pydantic.type(DependencyEdgeModel)
class DependencyEdge:
    id: str
    source: str
    target: str
    optional: bool
    dep_id: str
    reservation_id: str | None


@pydantic.type(ImplementationEdgeModel)
class ImplementationEdge:
    id: str
    source: str
    target: str
    reservation_id: str | None
    linked: bool = False


@pydantic.type(DependencyGraphModel)
class DependencyGraph:
    actions: list[ActionAction | InvalidAction | ImplementationAction]
    edges: list[DependencyEdge | ImplementationEdge]
