from typing import Any, Optional

import strawberry
from facade import enums, scalars
from pydantic import BaseModel
from rekuest_core import enums as renums
from rekuest_core import scalars as rscalars

from rekuest_core.inputs import models as rimodels
from rekuest_core.inputs import types as ritypes
from strawberry import LazyType
from strawberry.experimental import pydantic



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
    assignation_id: str | None = (
        None  # Was this reservation caused during an assignation and is tide to it?
    )
    instance_id: scalars.InstanceID
    node: strawberry.ID | None = None
    template: strawberry.ID | None = None
    title: str | None = None
    hash: rscalars.NodeHash | None = None
    reference: str | None = None
    binds: ritypes.BindsInput | None = None


class HookInputModel(BaseModel):
    kind: enums.HookKind
    hash: str


class AssignInputModel(BaseModel):
    instance_id: str
    node: str | None = None
    template: str | None = None
    reservation: str | None = None
    hooks: list[HookInputModel] | None = None
    args: dict[str, Any]
    reference: str | None = None
    parent: str | None = None
    cached: bool = False
    log: bool = False
    is_hook: bool = False


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


@pydantic.input(HookInputModel)
class HookInput:
    kind: enums.HookKind
    hash: str


@pydantic.input(AssignInputModel)
class AssignInput:
    instance_id: scalars.InstanceID
    node: strawberry.ID  | None = None
    template: strawberry.ID  | None = None
    hooks: list[HookInput] | None = strawberry.field(default_factory=list)
    reservation: strawberry.ID | None = None
    args: scalars.Args
    reference: str | None = None
    parent: strawberry.ID | None = None
    cached: bool = False
    log: bool = False
    is_hook: bool = False





@strawberry.input
class PortMatchInput:
    at: int | None = None
    key: str | None = None
    kind: renums.PortKind | None = None
    identifier: str | None = None
    nullable: bool | None = None
    children: Optional[list[LazyType["PortMatchInput", __name__]]] = None


@strawberry.input
class PortDemandInput:
    kind: enums.DemandKind
    matches: list[PortMatchInput] | None = None
    force_length: int | None = None
    force_non_nullable_length: int | None = None


class CreateTemplateInputModel(BaseModel):
    template: rimodels.TemplateInputModel
    instance_id: str
    extension: str


class CreateForeignTemplateInputModel(BaseModel):
    template: rimodels.TemplateInputModel
    instance_id: str
    extension: str



@pydantic.input(CreateTemplateInputModel)
class CreateTemplateInput:
    template: ritypes.TemplateInput
    instance_id: scalars.InstanceID
    extension: str

@pydantic.input(CreateForeignTemplateInputModel)
class CreateForeignTemplateInput:
    template: ritypes.TemplateInput
    agent: strawberry.ID
    extension: str


class DeleteTemplateInputModel(BaseModel):
    template: str

@pydantic.input(DeleteTemplateInputModel)
class DeleteTemplateInput:
    template: strawberry.ID


class SetExtensionTemplatesInputModel(BaseModel):
    template: rimodels.TemplateInputModel
    instance_id: str
    extension: str
    run_cleanup: bool = False



@pydantic.input(SetExtensionTemplatesInputModel)
class SetExtensionTemplatesInput:
    templates: list[ritypes.TemplateInput]
    extension: str
    run_cleanup: bool = False
    instance_id: scalars.InstanceID
