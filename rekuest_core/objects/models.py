import strawberry
from typing import Optional
from pydantic import BaseModel
from strawberry.experimental import pydantic
from typing import Literal, Union
import datetime
from rekuest_core import enums
from typing import Any

class ChoiceModel(BaseModel):
    label: str
    value: str
    description: str | None


class AssignWidgetModel(BaseModel):
    kind: str


class SliderAssignWidgetModel(AssignWidgetModel):
    kind: Literal["SLIDER"]
    min: int | None
    max: int | None


class ChoiceAssignWidgetModel(AssignWidgetModel):
    kind: Literal["CHOICE"]
    choices: list[ChoiceModel] | None


class CustomAssignWidgetModel(AssignWidgetModel):
    kind: Literal["CUSTOM"]
    hook: str
    ward: str


class SearchAssignWidgetModel(AssignWidgetModel):
    kind: Literal["SEARCH"]
    query: str  # TODO: Validators
    ward: str


class StringWidgetModel(AssignWidgetModel):
    kind: Literal["STRING"]
    placeholder: str
    as_paragraph: bool


AssignWidgetModelUnion = Union[
    SliderAssignWidgetModel, ChoiceAssignWidgetModel, SearchAssignWidgetModel
]


class ReturnWidgetModel(BaseModel):
    kind: str


class CustomReturnWidgetModel(ReturnWidgetModel):
    hook: str
    ward: str


class ChoiceReturnWidgetModel(ReturnWidgetModel):
    kind: Literal["CHOICE"]
    choices: list[ChoiceModel] | None


ReturnWidgetModelUnion = Union[CustomReturnWidgetModel, ChoiceReturnWidgetModel]


class EffectDependencyModel(BaseModel):
    condition: str
    key: str
    value: str


class EffectModel(BaseModel):
    dependencies: list[EffectDependencyModel]
    kind: str


class MessageEffectModel(EffectModel):
    kind: Literal["MESSAGE"]
    message: str


class CustomEffectModel(EffectModel):
    kind: Literal["CUSTOM"]
    hook: str
    ward: str


EffectModelUnion = Union[MessageEffectModel, CustomEffectModel]


class ChildPortModel(BaseModel):
    key: str 
    label: str | None
    scope: str
    kind: str
    description: str | None
    identifier: str | None
    nullable: bool
    default: str | None
    children: list["ChildPortModel"] | None
    assign_widget: AssignWidgetModelUnion | None
    return_widget: ReturnWidgetModelUnion | None


class BindsModel(BaseModel):
    templates: Optional[list[str]] = None
    clients: Optional[list[str]] = None
    desired_instances: int = 1
    minimum_instances: int = 1


class PortGroupModel(BaseModel):
    key: str
    hidden: bool


@pydantic.type(PortGroupModel)
class PortGroup:
    key: str
    hidden: bool


class ValidatorModel(BaseModel):
    function: str
    dependencies: list[str] | None = []
    label: str | None = None
    error_message: str | None = None


class PortModel(BaseModel):
    key: str
    scope: str
    label: str | None = None
    kind: str
    description: str | None = None
    identifier: str | None = None
    nullable: bool
    effects: list[EffectModelUnion] | None
    default: Any | None = None
    children: list[ChildPortModel] | None
    assign_widget: AssignWidgetModelUnion | None
    return_widget: ReturnWidgetModelUnion | None
    groups: list[str] | None
    validators: list[ValidatorModel] | None


class DefinitionModel(BaseModel):
    id: strawberry.ID
    hash: str
    name: str
    kind: enums.NodeKind
    description: str | None
    port_groups: list[PortGroup]
    collections: list[str]
    scope: enums.NodeScope
    is_test_for: list[str]
    tests: list[str]
    protocols: list[str]
    defined_at: datetime.datetime
