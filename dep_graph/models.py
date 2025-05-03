from pydantic import BaseModel, Field
import uuid


class InvalidActionModel(BaseModel):
    kind: str = "InvalidAction"
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    initial_hash: str


class ActionActionModel(BaseModel):
    kind: str = "ActionAction"
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    action_id: str
    name: str
    status: str | None
    reservation_id: str | None


class ImplementationActionModel(BaseModel):
    kind: str = "ImplementationAction"
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    implementation_id: str
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


ActionModel = ActionActionModel | InvalidActionModel | ImplementationActionModel
EdgeModel = DependencyEdgeModel | ImplementationEdgeModel


class DependencyGraphModel(BaseModel):
    actions: list[ActionModel]
    edges: list[EdgeModel]
