from facade import enums, scalars
import strawberry
from typing import Optional
from pydantic import BaseModel
from strawberry.experimental import pydantic
from typing import Any
from strawberry import LazyType


class BindsInputModel(BaseModel):
    templates: Optional[list[str]]
    clients: Optional[list[str]]
    desired_instances: int = 1


@pydantic.input(BindsInputModel)
class BindsInput:
    templates: list[strawberry.ID] | None
    clients: list[strawberry.ID] | None
    desired_instances: int | None


class EffectDependencyInputModel(BaseModel):
    key: str
    condition: str
    value: str


@pydantic.input(EffectDependencyInputModel)
class EffectDependencyInput:
    key: str
    condition: enums.LogicalCondition
    value: scalars.AnyDefault


class EffectInputModel(BaseModel):
    dependencies: list[EffectDependencyInputModel]
    kind: enums.EffectKind


@pydantic.input(EffectInputModel)
class EffectInput:
    dependencies: list[EffectDependencyInput]
    kind: enums.EffectKind


class ChoiceInputModel(BaseModel):
    value: str
    label: str
    description: str | None


@pydantic.input(ChoiceInputModel)
class ChoiceInput:
    value: scalars.AnyDefault
    label: str
    description: str | None


class AssignWidgetInputModel(BaseModel):
    kind: enums.AssignWidgetKind
    query: str | None = None
    choices: list[ChoiceInputModel] | None = None
    min: int | None = None
    max: int | None = None
    step: int | None = None
    placeholder: str | None = None
    hook: str | None = None
    ward: str | None = None


@pydantic.input(AssignWidgetInputModel)
class AssignWidgetInput:
    kind: enums.AssignWidgetKind
    query: scalars.SearchQuery | None = None
    choices: list[ChoiceInput] | None = None
    min: int | None = None
    max: int | None = None
    step: int | None = None
    placeholder: str | None = None
    as_paragraph: bool | None = None
    hook: str | None = None
    ward: str | None = None


class ReturnWidgetInputModel(BaseModel):
    kind: enums.ReturnWidgetKind
    query: str | None = None
    choices: list[ChoiceInputModel] | None = None
    min: int | None = None
    max: int | None = None
    step: int | None = None
    placeholder: str | None = None
    hook: str | None = None
    ward: str | None = None


@pydantic.input(ReturnWidgetInputModel)
class ReturnWidgetInput:
    kind: enums.ReturnWidgetKind
    query: scalars.SearchQuery | None = None
    choices: list[ChoiceInput] | None = None
    min: int | None = None
    max: int | None = None
    step: int | None = None
    placeholder: str | None = None
    hook: str | None = None
    ward: str | None = None


class ChildPortInputModel(BaseModel):
    label: str | None
    kind: enums.PortKind
    scope: enums.PortScope
    description: str | None = None
    child: Optional["ChildPortInputModel"] = None
    identifier: str | None = None
    nullable: bool
    variants: list["ChildPortInputModel"] | None = None
    effects: list[EffectInputModel] | None = None
    assign_widget: Optional["AssignWidgetInputModel"] = None
    return_widget: Optional["ReturnWidgetInputModel"] = None


@pydantic.input(ChildPortInputModel)
class ChildPortInput:
    label: str | None
    kind: enums.PortKind
    scope: enums.PortScope
    description: str | None = None
    child: Optional[LazyType["ChildPortInput", __name__]] = None
    identifier: scalars.Identifier | None = None
    nullable: bool
    default: scalars.AnyDefault | None = None
    variants: list[LazyType["ChildPortInput", __name__]] | None = strawberry.field(
        default_factory=list
    )
    effects: list[EffectInput] | None = strawberry.field(default_factory=list)
    assign_widget: Optional["AssignWidgetInput"] = None
    return_widget: Optional["ReturnWidgetInput"] = None


class PortInputModel(BaseModel):
    key: str
    scope: enums.PortScope
    label: str | None = None
    kind: enums.PortKind
    description: str | None = None
    identifier: str | None = None
    nullable: bool
    effects: list[EffectInputModel] | None
    validators: list[str]  = []
    default: Any | None = None
    child: ChildPortInputModel | None = None
    variants: list["ChildPortInputModel"] | None
    assign_widget: Optional["AssignWidgetInputModel"] = None
    return_widget: Optional["ReturnWidgetInputModel"] = None
    groups: list[str] | None


@pydantic.input(PortInputModel)
class PortInput:
    key: str
    scope: enums.PortScope
    label: str | None = None
    kind: enums.PortKind
    description: str | None = None
    identifier: str | None = None
    nullable: bool
    validators: list[scalars.Validator] | None = strawberry.field(default_factory=list)
    effects: list[EffectInput] | None = strawberry.field(default_factory=list)
    default: scalars.AnyDefault | None = None
    child: Optional[LazyType["ChildPortInput", __name__]] = None
    variants: list[LazyType["ChildPortInput", __name__]] | None = strawberry.field(
        default_factory=list
    )
    assign_widget: Optional["AssignWidgetInput"] = None
    return_widget: Optional["ReturnWidgetInput"] = None
    groups: list[str] | None = strawberry.field(default_factory=list)

class PortGroupInputModel(BaseModel):
    key: str
    hidden: bool


@pydantic.input(PortGroupInputModel)
class PortGroupInput:
    key: str
    hidden: bool


class DefinitionInputModel(BaseModel):
    description: str | None
    collections: list[str] = []
    name: str
    port_groups: list[PortGroupInputModel] = []
    args: list[PortInputModel]
    returns: list[PortInputModel]
    kind: enums.NodeKind
    is_test_for: list[str] = []
    interfaces: list[str] = []


@pydantic.input(DefinitionInputModel)
class DefinitionInput:
    """A definition for a template"""

    description: str | None = None
    collections: list[str] | None = strawberry.field(default_factory=list)
    name: str
    port_groups: list[PortGroupInput] | None = strawberry.field(default_factory=list)
    args: list[PortInput] | None = strawberry.field(default_factory=list)
    returns: list[PortInput] | None = strawberry.field(default_factory=list)
    kind: enums.NodeKind
    is_test_for: list[str] | None = strawberry.field(default_factory=list)
    interfaces: list[str] | None = strawberry.field(default_factory=list)


@strawberry.input
class DependencyInput:
    """A dependency for a template. By defining dependencies, you can
    create a dependency graph for your templates and nodes"""

    node: strawberry.ID | None = None
    hash: scalars.NodeHash | None = None
    reference: str | None = None  # How to reference this dependency (e.g. if it corresponds to a node_id in a flow)
    binds: BindsInput | None = None
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
    binds: BindsInput | None = None
