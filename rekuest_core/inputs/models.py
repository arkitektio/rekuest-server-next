from typing import Any, Optional
from rekuest_core import enums
from pydantic import BaseModel, Field


class BindsInputModel(BaseModel):
    templates: Optional[list[str]]
    clients: Optional[list[str]]
    desired_instances: int = 1


class EffectDependencyInputModel(BaseModel):
    key: str
    condition: str
    value: str


class EffectInputModel(BaseModel):
    dependencies: list[EffectDependencyInputModel]
    kind: enums.EffectKind


class ChoiceInputModel(BaseModel):
    value: str
    label: str
    description: str | None


class ValidatorInputModel(BaseModel):
    function: str
    dependencies: list[str] | None = []
    label: str | None = None

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


class PortInputModel(BaseModel):
    validators: list[ValidatorInputModel] | None
    key: str
    scope: enums.PortScope
    label: str | None = None
    kind: enums.PortKind
    description: str | None = None
    identifier: str | None = None
    nullable: bool
    effects: list[EffectInputModel] | None
    default: Any | None = None
    child: ChildPortInputModel | None = None
    variants: list["ChildPortInputModel"] | None
    assign_widget: Optional["AssignWidgetInputModel"] = None
    return_widget: Optional["ReturnWidgetInputModel"] = None
    groups: list[str] | None


class PortGroupInputModel(BaseModel):
    key: str
    hidden: bool


class DefinitionInputModel(BaseModel):
    """A definition for a template"""

    description: str = "No description provided"
    collections: list[str] = Field(default_factory=list)
    name: str
    port_groups: list[PortGroupInputModel] = Field(default_factory=list)
    args: list[PortInputModel] = Field(default_factory=list)
    returns: list[PortInputModel] = Field(default_factory=list)
    kind: enums.NodeKind
    is_test_for: list[str] = Field(default_factory=list)
    interfaces: list[str] = Field(default_factory=list)
