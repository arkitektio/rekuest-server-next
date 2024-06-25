from typing import Optional
from strawberry.experimental import pydantic
from strawberry import LazyType
from rekuest_core.inputs import models
import strawberry
from rekuest_core import enums, scalars


@pydantic.input(models.EffectDependencyInputModel)
class EffectDependencyInput:
    """An effect dependency is a dependency that is used to determine
    whether or not an effect should be applied to a port. For example,
    you could have an effect dependency that checks whether or not
    a port is null, and if it is, then the effect is applied.

    It is composed of a key, a condition, and a value. The key is the
    name of the port that the effect dependency is checking. The condition
    is the logical condition that the value should be checked against.



    """

    key: str
    condition: enums.LogicalCondition
    value: scalars.AnyDefault


@pydantic.input(models.EffectInputModel)
class EffectInput:
    """An effect is a way to modify a port based on a condition. For example,
    you could have an effect that sets a port to null if another port is null.

    Or, you could have an effect that hides the port if another port meets a condition.
    E.g when the user selects a certain option in a dropdown, another port is hidden.


    """
    kind: enums.EffectKind
    dependencies: list[EffectDependencyInput]
    label: str
    description: str | None


@pydantic.input(models.ChoiceInputModel)
class ChoiceInput:
    """A choice is a value that can be selected in a dropdown.

    It is composed of a value, a label, and a description. The value is the
    value that is returned when the choice is selected. The label is the
    text that is displayed in the dropdown. The description is the text
    that is displayed when the user hovers over the choice.

    """

    value: scalars.AnyDefault
    label: str
    description: str | None


@pydantic.input(models.AssignWidgetInputModel)
class AssignWidgetInput:
    """An Assign Widget is a UI element that is used to assign a value to a port.

    It gets displayed if we intend to assign to a node, and represents the Widget
    that gets displayed in the UI. For example, a dropdown, a text input, a slider,
    etc.

    This input type composes elements of all the different kinds of assign widgets.
    Please refere to each subtype for more information.



    """

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


@pydantic.input(models.ReturnWidgetInputModel)
class ReturnWidgetInput:
    """A Return Widget is a UI element that is used to display the value of a port.

    Return Widgets get displayed both if we show the return values of an assignment,
    but also when we inspect the given arguments of a previous run task. Their primary
    usecase is to adequately display the value of a port, in a user readable way.

    Return Widgets are often overwriten by the underlying UI framework (e.g. Orkestrator)
    to provide a better user experience. For example, a return widget that displays a
    date could be overwriten to display a calendar widget.

    Return Widgets provide more a way to customize this overwriten behavior.

    """

    kind: enums.ReturnWidgetKind
    query: scalars.SearchQuery | None = None
    choices: list[ChoiceInput] | None = None
    min: int | None = None
    max: int | None = None
    step: int | None = None
    placeholder: str | None = None
    hook: str | None = None
    ward: str | None = None


@pydantic.input(models.ChildPortInputModel)
class ChildPortInput:
    """A child port is a port that is nested inside another port. For example,

    a List of Integers has a governing port that is a list, and a child port that
    is of kind integer.

    """
    key: str 
    label: str | None
    kind: enums.PortKind
    scope: enums.PortScope
    description: str | None = None
    identifier: scalars.Identifier | None = None
    nullable: bool
    default: scalars.AnyDefault | None = None
    children: list[LazyType["ChildPortInput", __name__]] | None = strawberry.field(
        default_factory=list
    )
    effects: list[EffectInput] | None = strawberry.field(default_factory=list)
    assign_widget: Optional["AssignWidgetInput"] = None
    return_widget: Optional["ReturnWidgetInput"] = None





@pydantic.input(models.ValidatorInputModel)
class ValidatorInput:
    function: scalars.ValidatorFunction
    dependencies: list[str] | None = strawberry.field(default_factory=list)
    label: str | None = None
    error_message: str | None = None


@pydantic.input(models.PortInputModel)
class PortInput:
    """Port

    A Port is a single input or output of a node. It is composed of a key and a kind
    which are used to uniquely identify the port.

    If the Port is a structure, we need to define a identifier and scope,
    Identifiers uniquely identify a specific type of model for the scopes (e.g
    all the ports that have the identifier "@mikro/image" are of the same type, and
    are hence compatible with each other). Scopes are used to define in which context
    the identifier is valid (e.g. a port with the identifier "@mikro/image" and the
    scope "local", can only be wired to other ports that have the same identifier and
    are running in the same app). Global ports are ports that have the scope "global",
    and can be wired to any other port that has the same identifier, as there exists a
    mechanism to resolve and retrieve the object for each app. Please check the rekuest
    documentation for more information on how this works.


    """
    validators: list[ValidatorInput] | None = strawberry.field(default_factory=list)
    key: str
    scope: enums.PortScope
    label: str | None = None
    kind: enums.PortKind
    description: str | None = None
    identifier: str | None = None
    nullable: bool
    effects: list[EffectInput] | None = strawberry.field(default_factory=list)
    default: scalars.AnyDefault | None = None
    children: list[LazyType["ChildPortInput", __name__]] | None = strawberry.field(
        default_factory=list
    )
    assign_widget: Optional["AssignWidgetInput"] = None
    return_widget: Optional["ReturnWidgetInput"] = None
    groups: list[str] | None = strawberry.field(default_factory=list)


@strawberry.input()
class PortGroupInput:
    key: str
    hidden: bool

@pydantic.input(models.BindsInputModel)
class BindsInput:
    templates: Optional[list[str]]
    clients: Optional[list[str]]
    desired_instances: int = 1


@strawberry.input()
class DefinitionInput:
    """A definition

    Definitions are the building template for Nodes and provide the
    information needed to create a node. They are primarly composed of a name,
    a description, and a list of ports.

    Definitions provide a protocol of input and output, and do not contain
    any information about the actual implementation of the node ( this is handled
    by a template that implements a node).




    """

    description: str | None = None
    collections: list[str] = strawberry.field(default_factory=list)
    name: str
    port_groups: list[PortGroupInput] = strawberry.field(default_factory=list)
    args: list[PortInput] = strawberry.field(default_factory=list)
    returns: list[PortInput] = strawberry.field(default_factory=list)
    kind: enums.NodeKind
    is_test_for: list[str] = strawberry.field(default_factory=list)
    interfaces: list[str] = strawberry.field(default_factory=list)
    is_dev: bool = False

@pydantic.input(models.DependencyInputModel)
class DependencyInput:
    """A dependency for a template. By defining dependencies, you can
    create a dependency graph for your templates and nodes"""

    hash: scalars.NodeHash | None = None
    reference: str | None = (
        None  # How to reference this dependency (e.g. if it corresponds to a node_id in a flow)
    )
    binds: BindsInput | None = None
    optional: bool = False
    viable_instances: int | None = None



@pydantic.input(models.TemplateInputModel)
class TemplateInput:
    definition: DefinitionInput
    dependencies: list[DependencyInput] = strawberry.field(default_factory=list)
    interface: str
    params: scalars.AnyDefault | None = None
    dynamic: bool = False
    logo: str | None = None