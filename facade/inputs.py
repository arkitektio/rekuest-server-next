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

    node: strawberry.ID | None = None
    hash: scalars.NodeHash | None = None
    reference: str | None = None  # How to reference this dependency (e.g. if it corresponds to a node_id in a flow)
    binds: ritypes.BindsInput | None = None
    optional: bool = False
    viable_instances: int | None = None


@strawberry.input
class ReserveInput:
    instance_id: scalars.InstanceID
    node: strawberry.ID | None = None
    template: strawberry.ID | None = None
    title: str | None = None
    hash: scalars.NodeHash | None = None
    reference: str | None = None
    binds: ritypes.BindsInput | None = None


class CreateTemplateInputModel(BaseModel):
    definition: rimodels.DefinitionInputModel
    dependencies: DependencyInputModel | None = None
    interface: str
    params: dict[str, Any] | None = None
    instance_id: str | None = None


@pydantic.input(CreateTemplateInputModel)
class CreateTemplateInput:
    definition: ritypes.DefinitionInput
    dependencies: DependencyInput | None = None
    interface: str
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