import strawberry_django
from reaktion import models, scalars, enums, filters
import strawberry
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field
from strawberry.experimental import pydantic
from typing import Any, Dict
from typing import ForwardRef
from strawberry import LazyType
from typing import Literal, Union
from authentikate.strawberry.types import App, User
import datetime
from facade import types as facade_types
from facade import enums as facade_enums
from facade import scalars as facade_scalars


class PositionModel(BaseModel):
    x: float
    y: float


@pydantic.type(PositionModel)
class Position:
    x: float
    y: float


class GraphNodeModel(BaseModel):
    kind: enums.GraphNodeKind
    id: str
    position: PositionModel
    parent_node: str | None = None
    ins: list[list[facade_types.PortModel]]  # A set of streams
    outs: list[list[facade_types.PortModel]]
    constants: list[facade_types.PortModel]
    voids: list[facade_types.PortModel]
    constants_map: Dict[str, Any]
    globals_map: Dict[str, Any]
    description: str
    title: str


@pydantic.interface(GraphNodeModel)
class GraphNode:
    id: strawberry.ID
    kind: enums.GraphNodeKind
    position: Position
    parent_node: str | None = None
    ins: list[list[facade_types.Port]]  # Itmes that are streamed in
    outs: list[list[facade_types.Port]]  # Items that are streamed out
    constants: list[facade_types.Port]  # Items that are constants
    voids: list[facade_types.Port]  # Items that are voids
    constants_map: scalars.ValueMap
    globals_map: scalars.ValueMap
    description: str = "No description"
    title: str


class RetriableNodeModel(BaseModel):
    retries: int
    retry_delay: int


@pydantic.interface(RetriableNodeModel)
class RetriableNode:
    retries: int | None
    retry_delay: int | None


class AssignableNodeModel(BaseModel):
    next_timeout: int | None


@pydantic.interface(AssignableNodeModel)
class AssignableNode:
    next_timeout: int | None


class ArkitektGraphNodeModel(GraphNodeModel, RetriableNodeModel, AssignableNodeModel):
    kind: Literal["ARKITEKT"]
    hash: str
    map_strategy: str
    allow_local_execution: bool
    binds: facade_types.BindsModel
    node_kind: facade_enums.NodeKind

class ArkitektFilterGraphNodeModel(GraphNodeModel, RetriableNodeModel, AssignableNodeModel):
    kind: Literal["ARKITEKT_FILTER"]
    hash: str
    map_strategy: str
    allow_local_execution: bool
    binds: facade_types.BindsModel
    node_kind: facade_enums.NodeKind



@pydantic.type(ArkitektGraphNodeModel)
class ArkitektGraphNode(GraphNode, RetriableNode, AssignableNode):
    hash: str
    map_strategy: enums.MapStrategy
    allow_local_execution: bool
    binds: facade_types.Binds
    node_kind: facade_enums.NodeKind


@pydantic.type(ArkitektFilterGraphNodeModel)
class ArkitektFilterGraphNode(GraphNode, RetriableNode, AssignableNode):
    hash: str
    map_strategy: enums.MapStrategy
    allow_local_execution: bool
    binds: facade_types.Binds
    node_kind: facade_enums.NodeKind


class ArgNodeModel(GraphNodeModel):
    kind: Literal["ARGS"]
    arg_stuff: str | None = None


@pydantic.type(ArgNodeModel)
class ArgNode(GraphNode):
    arg_stuff: str | None = None


class ReactiveNodeModel(GraphNodeModel):
    kind: Literal["REACTIVE"]
    implementation: enums.ReactiveImplementation


@pydantic.type(ReactiveNodeModel)
class ReactiveNode(GraphNode):
    arg_stuff: str | None = None
    implementation: enums.ReactiveImplementation





class ReturnNodeModel(GraphNodeModel):
    kind: Literal["RETURNS"]
    return_stuff: str | None = None


@pydantic.type(ReturnNodeModel)
class ReturnNode(GraphNode):
    return_stuff: str | None = None


GraphNodeModelUnion = Union[
    ArkitektGraphNodeModel, ReactiveNodeModel, ArgNodeModel, ReturnNodeModel, ArkitektFilterGraphNodeModel
]


class StreamItemModel(BaseModel):
    kind: str
    label: str | None = None


@pydantic.type(StreamItemModel)
class StreamItem:
    kind: facade_enums.PortKind
    label: str


class GraphEdgeModel(BaseModel):
    kind: str
    id: str
    source: str
    target: str
    source_handle: str
    target_handle: str
    stream: list[StreamItemModel]


@pydantic.interface(GraphEdgeModel)
class GraphEdge:
    stream: list[StreamItem]
    id: strawberry.ID
    kind: enums.GraphEdgeKind
    source: str
    target: str
    source_handle: str
    target_handle: str


class VanillaEdgeModel(GraphEdgeModel):
    kind: Literal["VANILLA"]
    label: str | None = None


class LoggingEdgeModel(GraphEdgeModel):
    kind: Literal["LOGGING"]
    level: str


@pydantic.type(VanillaEdgeModel)
class VanillaEdge(GraphEdge):
    label: str | None = None


@pydantic.type(LoggingEdgeModel)
class LoggingEdge(GraphEdge):
    level: facade_enums.LogLevel


StreamEdgeModelUnion = Union[VanillaEdgeModel, LoggingEdgeModel]


class GlobalArgModel(BaseModel):
    key: str
    port: facade_types.PortModel


@pydantic.type(GlobalArgModel)
class GlobalArg:
    key: str
    port: facade_types.Port


class GraphModel(BaseModel):
    zoom: str | None = None
    nodes: list[GraphNodeModelUnion]
    edges: list[StreamEdgeModelUnion]
    globals: list[GlobalArgModel]


@pydantic.type(GraphModel)
class Graph:
    zoom: float
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    globals: list[GlobalArg]


@strawberry_django.type(models.Flow, filters=filters.FlowFilter, pagination=True)
class Flow:
    id: strawberry.ID
    title: str
    description: str | None = None
    created_at: datetime.datetime
    workspace: "Workspace"

    @strawberry_django.field()
    def graph(self, info) -> Graph:
        print(GraphModel(**self.graph))

        return GraphModel(**self.graph)


@strawberry_django.type(
    models.Workspace, filters=filters.WorkspaceFilter, pagination=True
)
class Workspace:
    id: strawberry.ID
    title: str
    description: str | None = None

    @strawberry_django.field()
    def latest_flow(self, info) -> Optional[Flow]:
        return self.flows.order_by("-created_at").first()


@strawberry_django.type(
    models.ReactiveTemplate, filters=filters.ReactiveTemplateFilter, pagination=True
)
class ReactiveTemplate:
    id: strawberry.ID
    implementation: enums.ReactiveImplementation
    title: str
    description: str | None = None

    @strawberry_django.field()
    def ins(self, info) -> list[list[facade_types.Port]]:
        return [[facade_types.PortModel(**i) for i in stream] for stream in self.ins]

    @strawberry_django.field()
    def outs(self, info) -> list[list[facade_types.Port]]:
        return [[facade_types.PortModel(**i) for i in stream] for stream in self.outs]

    @strawberry_django.field()
    def constants(self, info) -> list[facade_types.Port]:
        return [facade_types.PortModel(**i) for i in self.constants]
    
    @strawberry_django.field()
    def voids(self, info) -> list[facade_types.Port]:
        return []


@strawberry_django.type(models.Run, pagination=True)
class Run:
    id: strawberry.ID


@strawberry_django.type(models.RunSnapshot, pagination=True)
class RunSnapshot:
    id: strawberry.ID


@strawberry_django.type(models.RunEvent, pagination=True)
class RunEvent:
    id: strawberry.ID


@strawberry_django.type(models.Trace, pagination=True)
class Trace:
    id: strawberry.ID


@strawberry_django.type(models.TraceSnapshot, pagination=True)
class TraceSnapshot:
    id: strawberry.ID


@strawberry_django.type(models.TraceEvent, pagination=True)
class TraceEvent:
    id: strawberry.ID
