import strawberry

from strawberry.experimental import pydantic
from pydantic import BaseModel
from facade import inputs as facade_inputs
from facade import enums as facade_enums
from reaktion import scalars, enums
from typing import Any, Dict


class PositionInputModel(BaseModel):
    x: float
    y: float


@pydantic.input(PositionInputModel)
class PositionInput:
    x: float
    y: float


class GraphNodeInputModel(BaseModel):
    id: str
    kind: enums.GraphNodeKind
    position: PositionInput
    parent_node: str | None = None
    ins: list[list[facade_inputs.PortInputModel]]  # A set of streams
    outs: list[list[facade_inputs.PortInputModel]]
    constants: list[facade_inputs.PortInputModel]
    constants_map: Dict[str, Any]
    globals_map: Dict[str, Any]
    description: str | None = None
    title: str | None = None
    retries: int | None = None
    retry_delay: int | None = None
    node_kind: facade_enums.NodeKind | None = None
    next_timeout: int | None = None
    hash: str | None = None
    map_strategy: enums.MapStrategy | None = None
    allow_local_execution: bool | None = None
    binds: facade_inputs.BindsInputModel | None = None
    implementation: enums.ReactiveImplementation | None = None


@pydantic.input(GraphNodeInputModel)
class GraphNodeInput:
    id: str
    kind: enums.GraphNodeKind
    position: PositionInput
    parent_node: str | None = None
    ins: list[list[facade_inputs.PortInput]]  # A set of streams
    outs: list[list[facade_inputs.PortInput]]
    constants: list[facade_inputs.PortInput]
    constants_map: scalars.ValueMap
    globals_map: scalars.ValueMap
    description: str | None = None
    title: str | None = None
    retries: int | None = None
    retry_delay: int | None = None
    node_kind: facade_enums.NodeKind | None = None
    next_timeout: int | None = None
    hash: str | None = None
    map_strategy: enums.MapStrategy | None = None
    allow_local_execution: bool | None = None
    binds: facade_inputs.BindsInput | None = None
    parent_node: str | None = None
    implementation: enums.ReactiveImplementation | None = None


class StreamItemInputModel(BaseModel):
    kind: str
    label: str | None = None


@pydantic.input(StreamItemInputModel)
class StreamItemInput:
    kind: facade_enums.PortKind
    label: str


class GraphEdgeInputModel(BaseModel):
    kind: str
    id: str
    source: str
    target: str
    source_handle: str
    target_handle: str
    stream: list[StreamItemInputModel]


@pydantic.input(GraphEdgeInputModel)
class GraphEdgeInput:
    kind: enums.GraphEdgeKind
    id: str
    source: str
    target: str
    source_handle: str
    target_handle: str
    stream: list[StreamItemInput]
    label: str | None = None
    level: str | None = None


class GlobalArgInputModel(BaseModel):
    key: str
    port: facade_inputs.PortInputModel


@pydantic.input(GlobalArgInputModel)
class GlobalArgInput:
    key: str
    port: facade_inputs.PortInput


class GraphInputModel(BaseModel):
    nodes: list[GraphNodeInputModel]
    edges: list[GraphEdgeInputModel]
    globals: list[GlobalArgInputModel]


@pydantic.input(GraphInputModel, all_fields=True)
class GraphInput:
    pass


class ReactiveTemplateInputModel(BaseModel):
    title: str
    description: str
    ins: list[list[facade_inputs.PortInputModel]]  # A set of streams
    outs: list[list[facade_inputs.PortInputModel]]
    constants: list[facade_inputs.PortInputModel]
    implementation: enums.ReactiveImplementation

    class Config:
        use_enum_values = True


@pydantic.input(ReactiveTemplateInputModel, all_fields=True)
class ReactiveTemplateInput:
    pass
