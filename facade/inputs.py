from facade import enums, scalars
import strawberry
from typing import Optional
from pydantic import BaseModel
from strawberry.experimental import pydantic
from typing import Any
from strawberry import LazyType
from rekuest_core.inputs import types as ritypes
from rekuest_core import scalars as rscalars    



@strawberry.input
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

@strawberry.input
class CreateTemplateInput:
    definition: ritypes.DefinitionInput
    dependencies: DependencyInput | None = None
    interface: str
    params: rscalars.AnyDefault | None = None
    instance_id: scalars.InstanceID | None = None