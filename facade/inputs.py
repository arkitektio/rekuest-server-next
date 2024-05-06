from facade import enums, scalars
import strawberry
from typing import Optional, Any
from pydantic import BaseModel
from strawberry.experimental import pydantic
from typing import Any
from strawberry import LazyType
from rekuest_core.inputs import types as ritypes
from rekuest_core.inputs import models as rimodels
from rekuest_core import enums as renums
from rekuest_core import scalars as rscalars    

class DependencyInputModel(BaseModel):
    node: str
    hash: str
    reference: str  | None
    binds: rimodels.BindsInputModel | None
    optional: bool = False
    viable_instances: int | None


@pydantic.input(DependencyInputModel)
class DependencyInput:
    """A dependency for a template. By defining dependencies, you can
    create a dependency graph for your templates and nodes"""
    hash: scalars.NodeHash | None = None
    reference: str | None = None  # How to reference this dependency (e.g. if it corresponds to a node_id in a flow)
    binds: ritypes.BindsInput | None = None
    optional: bool = False
    viable_instances: int | None = None


class ReserveInputModel(BaseModel):
    instance_id: str
    node: str | None = None
    template: str | None = None
    title: str | None = None
    hash: str | None = None
    reference: str | None = None
    binds: rimodels.BindsInputModel | None = None

    


@pydantic.input(ReserveInputModel)
class ReserveInput:
    instance_id: scalars.InstanceID
    node: strawberry.ID | None = None
    template: strawberry.ID | None = None
    title: str | None = None
    hash: scalars.NodeHash | None = None
    reference: str | None = None
    binds: ritypes.BindsInput | None = None


class AssignInputModel(BaseModel):
    reservation: str
    args: list[Any | None]
    reference: str | None = None
    parent: str | None = None
    cached: bool = False
    log: bool = False



class CancelInputModel(BaseModel):
    assignation: str

@pydantic.input(CancelInputModel)
class CancelInput:
    assignation: strawberry.ID


class InterruptInputModel(BaseModel):
    assignation: str

@pydantic.input(InterruptInputModel)
class InterruptInput:
    assignation: strawberry.ID



@pydantic.input(AssignInputModel)
class AssignInput:
    reservation: strawberry.ID
    args: list[scalars.Arg | None]
    reference: str | None = None
    parent: strawberry.ID | None = None
    cached: bool = False
    log: bool = False


class CreateTemplateInputModel(BaseModel):
    definition: rimodels.DefinitionInputModel
    dependencies: DependencyInputModel | None = None
    interface: str
    extension: str
    params: dict[str, Any] | None = None
    instance_id: str | None = None


@pydantic.input(CreateTemplateInputModel)
class CreateTemplateInput:
    definition: ritypes.DefinitionInput
    dependencies: list[DependencyInput] | None = None
    interface: str
    extension: str
    params: rscalars.AnyDefault | None = None
    instance_id: scalars.InstanceID | None = None

@strawberry.input
class PortMatchInput:
    at: int | None = None
    key: str | None  = None
    kind: renums.PortKind | None  = None
    identifier: str | None  = None
    nullable: bool | None  = None
    variants: Optional[list[LazyType["PortDemandInput", __name__]]]  = None
    child: Optional[LazyType["PortDemandInput", __name__]]  = None
 


@strawberry.input
class PortDemandInput:
    kind: enums.DemandKind
    matches: list[PortMatchInput] | None = None
    force_length: int | None = None
    force_non_nullable_length: int | None = None