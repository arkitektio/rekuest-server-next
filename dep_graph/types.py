import datetime
from typing import Optional

import strawberry
import strawberry_django
from pydantic import BaseModel
from strawberry import LazyType
from strawberry.experimental import pydantic


from .models import NodeNodeModel, InvalidNodeModel, TemplateNodeModel, DependencyEdgeModel, DependencyGraphModel, ImplementationEdgeModel




@pydantic.type(NodeNodeModel)
class NodeNode:
    id: str
    node_id: str
    name: str
    status: str | None
    reservation_id: str | None


@pydantic.type(InvalidNodeModel)
class InvalidNode:
    id: str
    initial_hash: str



@pydantic.type(TemplateNodeModel)
class TemplateNode:
    id: str
    template_id: str
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
    nodes: list[NodeNode | InvalidNode | TemplateNode]
    edges: list[DependencyEdge | ImplementationEdge]



