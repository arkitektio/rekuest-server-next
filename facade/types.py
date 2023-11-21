import strawberry_django
from facade import models, scalars, enums, filters
import strawberry
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field
from strawberry.experimental import pydantic
from typing import Any
from typing import ForwardRef
from strawberry import LazyType
from typing import Literal, Union
from authentikate.strawberry.types import App, User
import datetime


class ChoiceModel(BaseModel):
    label: str
    value: str
    description: str | None


@pydantic.type(ChoiceModel, fields=["label", "value", "description"])
class Choice:
    pass


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


@pydantic.interface(AssignWidgetModel)
class AssignWidget:
    kind: enums.AssignWidgetKind


@pydantic.type(SliderAssignWidgetModel)
class SliderAssignWidget(AssignWidget):
    min: int | None
    max: int | None


@pydantic.type(ChoiceAssignWidgetModel)
class ChoiceAssignWidget(AssignWidget):
    choices: strawberry.auto


@pydantic.type(CustomAssignWidgetModel)
class CustomAssignWidget(AssignWidget):
    hook: str
    ward: str


@pydantic.type(SearchAssignWidgetModel)
class SearchAssignWidget(AssignWidget):
    query: str
    ward: str


@pydantic.type(StringWidgetModel)
class StringAssignWidget(AssignWidget):
    placeholder: str
    as_paragraph: bool


@pydantic.interface(ReturnWidgetModel)
class ReturnWidget:
    kind: enums.ReturnWidgetKind


@pydantic.type(CustomReturnWidgetModel)
class CustomReturnWidget(ReturnWidget):
    hook: str
    ward: str


@pydantic.type(ChoiceReturnWidgetModel)
class ChoiceReturnWidget(ReturnWidget):
    choices: strawberry.auto


class EffectDependencyModel(BaseModel):
    condition: str
    key: str
    value: str


@pydantic.type(EffectDependencyModel)
class EffectDependency:
    condition: enums.LogicalCondition
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


@pydantic.interface(EffectModel)
class Effect:
    kind: str
    dependencies: list[EffectDependency]
    pass


@pydantic.type(MessageEffectModel)
class MessageEffect(Effect):
    message: str


@pydantic.type(CustomEffectModel)
class CustomEffect(Effect):
    ward: str
    hook: str


EffectModelUnion = Union[MessageEffectModel, CustomEffectModel]


class ChildPortModel(BaseModel):
    label: str | None
    scope: str
    kind: str
    child: Optional["ChildPortModel"] = None
    description: str | None
    identifier: str | None
    nullable: bool
    default: str | None
    variants: list["ChildPortModel"] | None
    assign_widget: AssignWidgetModelUnion | None
    return_widget: ReturnWidgetModelUnion | None


class BindsModel(BaseModel):
    templates: Optional[list[str]] = None
    clients: Optional[list[str]] = None
    desired_instances: int = 1
    minimum_instances: int = 1


@pydantic.type(BindsModel)
class Binds:
    templates: list[strawberry.ID]
    clients: list[strawberry.ID]
    desired_instances: int


@pydantic.type(ChildPortModel)
class ChildPort:
    label: strawberry.auto
    identifier: scalars.Identifier | None
    default: scalars.AnyDefault | None
    scope: enums.PortScope
    kind: enums.PortKind
    nullable: bool
    child: Optional[
        LazyType["ChildPort", __name__]
    ] = None  # this took me a while to figure out should be more obvious
    variants: Optional[
        list[LazyType["ChildPort", __name__]]
    ] = None  # this took me a while to figure out should be more obvious
    assign_widget: AssignWidget | None
    return_widget: ReturnWidget | None


class PortGroupModel(BaseModel):
    key: str
    hidden: bool


@pydantic.type(PortGroupModel)
class PortGroup:
    key: str
    hidden: bool


class PortModel(BaseModel):
    key: str
    scope: str
    label: str | None = None
    kind: str
    description: str | None = None
    identifier: str | None = None
    nullable: bool
    effects: list[EffectModelUnion] | None
    default: str | None
    variants: list[ChildPortModel] | None
    assign_widget: AssignWidgetModelUnion | None
    return_widget: ReturnWidgetModelUnion | None
    child: Optional[ChildPortModel] = None
    groups: list[str] | None


@pydantic.type(PortModel)
class Port:
    identifier: scalars.Identifier | None
    default: scalars.AnyDefault | None
    scope: enums.PortScope
    kind: enums.PortKind
    key: str
    nullable: bool
    label: str | None
    description: str | None
    effects: list[Effect] | None
    child: Optional[ChildPort] = None
    variants: list[ChildPort] | None = None
    assign_widget: AssignWidget | None
    return_widget: ReturnWidget | None
    groups: list[str] | None


@strawberry_django.type(models.Registry)
class Registry:
    id: strawberry.ID
    app: App
    user: User
    agents: list["Agent"]


@strawberry_django.type(models.Collection)
class Collection:
    id: strawberry.ID
    name: str
    nodes: list["Node"]


@strawberry_django.type(models.Protocol)
class Protocol:
    id: strawberry.ID
    name: str
    nodes: list["Node"]


@strawberry_django.type(
    models.Node, filters=filters.NodeFilter, pagination=True, order=filters.NodeOrder
)
class Node:
    id: strawberry.ID
    hash: scalars.NodeHash
    name: str
    kind: enums.NodeKind
    description: str | None
    port_groups: list[PortGroup]
    collections: list["Collection"]
    templates: list["Template"]
    scope: enums.NodeScope
    is_test_for: list["Node"]
    tests: list["Node"]
    protocols: list["Protocol"]
    defined_at: datetime.datetime

    @strawberry_django.field()
    def args(self) -> list[Port]:
        return [PortModel(**i) for i in self.args]

    @strawberry_django.field()
    def returns(self) -> list[Port]:
        return [PortModel(**i) for i in self.returns]


@strawberry_django.type(
    models.Template, filters=filters.TemplateFilter, pagination=True
)
class Template:
    id: strawberry.ID
    name: str | None
    interface: str
    agent: "Agent"
    node: "Node"
    params: scalars.AnyDefault


@strawberry_django.type(models.Agent, filters=filters.AgentFilter, pagination=True)
class Agent:
    id: strawberry.ID
    instance_id: scalars.InstanceID
    registry: "Registry"


@strawberry_django.type(models.Waiter, filters=filters.WaiterFilter, pagination=True)
class Waiter:
    id: strawberry.ID
    instance_id: scalars.InstanceID
    registry: "Registry"


@strawberry_django.type(
    models.Provision, filters=filters.ProvisionFilter, pagination=True
)
class Provision:
    id: strawberry.ID
    name: str
    agent: "Agent"
    template: "Template"
    status: enums.ProvisionStatus


@strawberry_django.type(
    models.ProvisionEvent, filters=filters.ProvisionEventFilter, pagination=True
)
class ProvisionEvent:
    id: strawberry.ID
    provision: "Provision"
    kind: enums.ProvisionEventKind
    level: enums.LogLevel
    created_at: strawberry.auto


@strawberry_django.type(
    models.Reservation, filters=filters.ReservationFilter, pagination=True
)
class Reservation:
    id: strawberry.ID
    name: str
    waiter: "Waiter"
    title: str | None
    node: "Node"
    status: enums.ReservationStatus
    updated_at: datetime.datetime
    reference: str
    provisions: list["Provision"]
    binds: Binds | None


@strawberry_django.type(
    models.ReservationEvent, filters=filters.ReservationEventFilter, pagination=True
)
class ReservationEvent:
    id: strawberry.ID
    reservation: "Reservation"
    kind: enums.ReservationEventKind
    level: enums.LogLevel
    created_at: strawberry.auto


@strawberry_django.type(
    models.Assignation, filters=filters.AssignationFilter, pagination=True
)
class Assignation:
    id: strawberry.ID
    name: str
    reference: str | None
    args: scalars.AnyDefault
    parent: "Assignation"
    status: enums.AssignationStatus
    status_message: str | None
    waiter: "Waiter"
    node: "Node"
    events: list["AssignationEvent"]
    created_at: datetime.datetime
    updated_at: datetime.datetime


@strawberry_django.type(
    models.AssignationEvent, filters=filters.AssignationEventFilter, pagination=True
)
class AssignationEvent:
    id: strawberry.ID
    name: str
    returns: scalars.AnyDefault
    assignation: "Assignation"
    kind: enums.AssignationEventKind
    level: enums.LogLevel
    created_at: strawberry.auto


@strawberry_django.type(
    models.TestCase, filters=filters.TestCaseFilter, pagination=True
)
class TestCase:
    id: strawberry.ID
    key: str
    node: "Node"
    is_benchmark: bool
    description: str
    name: str
    results: list["TestResult"]


@strawberry_django.type(
    models.TestResult, filters=filters.TestResultFilter, pagination=True
)
class TestResult:
    id: strawberry.ID
    template: "Template"
    case: "TestCase"
    passed: bool
    created_at: datetime.datetime
    updated_at: datetime.datetime
