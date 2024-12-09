from pydantic import BaseModel, Field
import uuid


class InvalidNodeModel(BaseModel):
    kind: str = "InvalidNode"
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    initial_hash: str


class NodeNodeModel(BaseModel):
    kind: str = "NodeNode"
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    node_id: str
    name: str
    status: str | None
    reservation_id: str | None


class TemplateNodeModel(BaseModel):
    kind: str = "TemplateNode"
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    template_id: str
    interface: str
    client_id: str
    status: str | None
    provision_id: str | None
    reservation_id: str | None
    linked: bool = False
    active: bool = False


class DependencyEdgeModel(BaseModel):
    kind: str = "DependencyEdge"
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source: str
    target: str
    optional: bool
    dep_id: str | None
    reservation_id: str | None


class ImplementationEdgeModel(BaseModel):
    kind: str = "ImplementationEdge"
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source: str
    target: str
    optional: bool
    reservation_id: str | None
    linked: bool = False


NodeModel = NodeNodeModel | InvalidNodeModel | TemplateNodeModel
EdgeModel = DependencyEdgeModel | ImplementationEdgeModel


class DependencyGraphModel(BaseModel):
    nodes: list[NodeModel]
    edges: list[EdgeModel]
