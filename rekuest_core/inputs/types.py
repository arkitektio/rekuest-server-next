from typing import Annotated, List, Optional
from strawberry.experimental import pydantic
from strawberry import LazyType
from rekuest_core.inputs import models
import strawberry
from rekuest_core import enums, scalars

# NOTE: For ``@strawberry.experimental.pydantic`` types, GraphQL field descriptions are
# sourced from the *pydantic* model (``Field(description=...)`` in ``models.py``), not from
# ``strawberry.field(description=...)``. The pydantic models are therefore the single source
# of truth for field documentation. Type-level descriptions (passed to the decorator or via a
# class docstring) still work here and are kept. Pure ``@strawberry.input`` types that are not
# backed by a pydantic model (``PortGroupInput``, ``DefinitionInput``) keep their field-level
# descriptions because those are read directly by strawberry.


@pydantic.input(
    models.EffectInputModel,
    description="""
                 An effect is a way to modify a port based on a condition. For example,
    you could have an effect that sets a port to null if another port is null.

    Or, you could have an effect that hides the port if another port meets a condition.
    E.g when the user selects a certain option in a dropdown, another port is hidden.


    """,
)
class EffectInput:
    kind: enums.EffectKind
    dependencies: list[str] | None = strawberry.field(default_factory=list)
    function: scalars.ValidatorFunction
    message: str | None = None
    hook: str | None = None
    ward: str | None = None
    fade: bool | None = True


@pydantic.input(
    models.ChoiceInputModel,
    description="""
A choice is a value that can be selected in a dropdown.

It is composed of a value, a label, and a description. The value is the
value that is returned when the choice is selected. The label is the
text that is displayed in the dropdown. The description is the text
that is displayed when the user hovers over the choice.

    """,
)
class ChoiceInput:
    value: scalars.AnyDefault
    label: str
    image: str | None = None
    description: str | None = None


@pydantic.input(models.StateAccessorInputModel)
class StateAccessorInput:
    option_key: enums.OptionKey
    sub_path: str | None = None


@pydantic.input(models.AssignWidgetInputModel)
class AssignWidgetInput:
    """An Assign Widget is a UI element that is used to assign a value to a port.

    It gets displayed if we intend to assign to a action, and represents the Widget
    that gets displayed in the UI. For example, a dropdown, a text input, a slider,
    etc.

    This input type composes elements of all the different kinds of assign widgets.
    Please refere to each subtype for more information.



    """

    kind: enums.AssignWidgetKind
    query: scalars.SearchQuery | None = None
    choices: list[ChoiceInput] | None = None
    state_choices: str | None = None
    follow_value: str | None = None
    min: float | None = None
    max: float | None = None
    step: float | None = None
    placeholder: str | None = None
    as_paragraph: bool | None = None
    hook: str | None = None
    ward: str | None = None
    fallback: Optional[Annotated["AssignWidgetInput", strawberry.lazy(__name__)]] = None
    filters: Optional[List[Annotated["ArgPortInput", strawberry.lazy(__name__)]]] = strawberry.field(default_factory=list)
    dependencies: list[str] | None = strawberry.field(default_factory=list)
    dependency: str | None = None
    state_path: str | None = None
    target_dependency: str | None = None
    target_action: str | None = None
    target_port: str | None = None
    state_accessors: Optional[List[Annotated["StateAccessorInput", strawberry.lazy(__name__)]]] = None


@pydantic.input(
    models.ReturnWidgetInputModel,
    description="""A Return Widget is a UI element that is used to display the value of a port.

    Return Widgets get displayed both if we show the return values of an assignment,
    but also when we inspect the given arguments of a previous run task. Their primary
    usecase is to adequately display the value of a port, in a user readable way.

    Return Widgets are often overwriten by the underlying UI framework (e.g. Orkestrator)
    to provide a better user experience. For example, a return widget that displays a
    date could be overwriten to display a calendar widget.

    Return Widgets provide more a way to customize this overwriten behavior.

    """,
)
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


@pydantic.input(
    models.ValidatorInputModel,
    description="""
A validating function for a port. Can specify a function that will run when validating values of the port.
If outside dependencies are needed they need to be specified in the dependencies field. With the .. syntax
when transversing the tree of ports.

""",
)
class ValidatorInput:
    function: scalars.ValidatorFunction
    dependencies: list[str] | None = strawberry.field(default_factory=list)
    label: str | None = None
    error_message: str | None = None


@pydantic.input(
    models.OptimisticInputModel,
    description=""" An optimistic is used to optimistically set state values when the action is assigned. This is used to provide a better user experience by optimistically setting state values when the action is assigned, instead of waiting for the action to be executed and the state to be updated. This will only ever happen on the frontend.

""",
)
class OptimisticInput:
    state: str
    path: str
    accessor: str | None = None


@pydantic.input(models.RequiresInputModel)
class RequiresInput:
    key: str
    operator: enums.RequiresOperator
    value: scalars.Arg


@pydantic.input(models.ProvidesInputModel)
class ProvidesInput:
    key: str
    operator: enums.ProvidesOperator
    value: scalars.Arg


@pydantic.input(
    models.ArgPortInputModel,
    description="""Port

    A Port is a single input or output of a action. It is composed of a key and a kind
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


    """,
)
class ArgPortInput:
    validators: list[ValidatorInput] | None = strawberry.field(default_factory=list)
    key: str
    label: str | None = None
    kind: enums.PortKind
    description: str | None = None
    identifier: str | None = None
    nullable: bool = False
    effects: list[EffectInput] | None = strawberry.field(default_factory=list)
    choices: list[ChoiceInput] | None = strawberry.field(default_factory=list)
    default: scalars.AnyDefault | None = None
    children: list[Annotated["ArgPortInput", strawberry.lazy(__name__)]] | None = strawberry.field(default_factory=list)
    widget: Optional["AssignWidgetInput"] = None
    requires: list[RequiresInput] | None = strawberry.field(default_factory=list)


@pydantic.input(
    models.ReturnPortInputModel,
    description="""Port

    A Port is a single input or output of a action. It is composed of a key and a kind
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


    """,
)
class ReturnPortInput:
    validators: list[ValidatorInput] | None = strawberry.field(default_factory=list)
    key: str
    label: str | None = None
    kind: enums.PortKind
    description: str | None = None
    identifier: str | None = None
    nullable: bool = False
    effects: list[EffectInput] | None = strawberry.field(default_factory=list)
    choices: list[ChoiceInput] | None = strawberry.field(default_factory=list)
    default: scalars.AnyDefault | None = None
    children: list[Annotated["ReturnPortInput", strawberry.lazy(__name__)]] | None = strawberry.field(default_factory=list)
    widget: Optional["ReturnWidgetInput"] = None
    provides: list[ProvidesInput] | None = strawberry.field(default_factory=list)


@strawberry.input(
    description="A Port Group is a group of ports that are related to each other. It is used to group ports together in the UI and provide a better user experience.",
)
class PortGroupInput:
    key: str = strawberry.field(description="The key of the port group. This is used to uniquely identify the port group")
    title: str | None
    description: str | None
    effects: list[EffectInput] | None = strawberry.field(default_factory=list)
    ports: list[str] | None = strawberry.field(default_factory=list)


@pydantic.input(
    models.PortMatchInputModel,
    description="""A dependency for a implementation. By defining dependencies, you can
    create a dependency graph for your implementations and actions""",
)
class PortMatchInput:
    at: int | None = None
    key: str | None = None
    kind: enums.PortKind | None = None
    identifier: str | None = None
    nullable: bool | None = None
    children: Optional[list[Annotated["PortMatchInput", strawberry.lazy(__name__)]]] = None


@pydantic.input(
    models.ActionDependencyInputModel,
    description="""A dependency for a implementation. By defining dependencies, you can
    create a dependency graph for your implementations and actions""",
)
class ActionDependencyInput:
    key: str
    version: str | None = None
    app: str | None = None
    allow_inactive: bool | None = None
    name: str | None = None
    action_key: str | None = None
    description: str | None = None
    arg_matches: list[PortMatchInput] | None = None
    return_matches: list[PortMatchInput] | None = None
    protocols: list[strawberry.ID] | None = None
    force_arg_length: int | None = None
    force_return_length: int | None = None
    optional: bool = False


@pydantic.input(
    models.StateDependencyInputModel,
    description="""A dependency for a implementation. By defining dependencies, you can
    create a dependency graph for your implementations and actions""",
)
class StateDependencyInput:
    key: str
    version: str | None = None
    app: str | None = None
    state_key: str | None = None
    allow_inactive: bool | None = None
    name: str | None = None
    description: str | None = None
    port_matches: list[PortMatchInput] | None = None
    protocols: list[strawberry.ID] | None = None
    optional: bool = False


@pydantic.input(
    models.AgentDependencyInputModel,
    description="""A dependency for a implementation. By defining dependencies, you can
    create a dependency graph for your implementations and actions""",
)
class AgentDependencyInput:
    key: str
    app: str | None = None
    version: str | None = None
    auto_resolvable: bool = False
    name: str | None = None
    description: str | None = None
    optional: bool = False
    action_demands: list[ActionDependencyInput] | None = None
    state_demands: list[StateDependencyInput] | None = None
    min_viable_instances: int | None = None
    max_viable_instances: int | None = None
    mutually_exclusive_keys: list[str] | None = None
    prefered_instances: int | None = None
    assign_policy: enums.AssignPolicy = enums.AssignPolicy.BALANCED


@strawberry.input(
    description="""A definition

    Definitions are the building implementation for Actions and provide the
    information needed to create a action. They are primarly composed of a name,
    a description, and a list of ports.

    Definitions provide a protocol of input and output, and do not contain
    any information about the actual implementation of the action ( this is handled
    by a implementation that implements a action).

    """,
)
class DefinitionInput:
    description: str | None = strawberry.field(
        default=None,
        description="The description of the definition. This is the text that is displayed in the UI",
    )
    collections: list[str] = strawberry.field(
        default_factory=list,
        description="The collections of the definition. This is used to group definitions together in the UI",
    )
    key: str = strawberry.field(description="The key of the definition. This is used to uniquely identify the definition")
    package: str | None = strawberry.field(
        default=None,
        description="The package of the function. Will default to the currents agent's app if not specified. This is used to group definitions together in the UI and provide a better user experience",
    )
    version: str = strawberry.field(description="The version of the definition. This is used to differentiate if the underyling algorithm has changed, i.e we would expect different results for the same input")
    name: str = strawberry.field(description="The name of the actions. This is used to uniquely identify the definition")
    stateful: bool = strawberry.field(
        default=False,
        description="Whether the definition is stateful or not. If the definition is stateful, it can be used to create a stateful action. If the definition is not stateful, it cannot be used to create a stateful action",
    )
    port_groups: list[PortGroupInput] = strawberry.field(
        default_factory=list,
        description="The port groups of the definition. This is used to group ports together in the UI",
    )
    args: list[ArgPortInput] = strawberry.field(
        default_factory=list,
        description="The args of the definition. This is the input ports of the definition",
    )
    returns: list[ReturnPortInput] = strawberry.field(
        default_factory=list,
        description="The returns of the definition. This is the output ports of the definition",
    )
    tests: ActionDependencyInput | None = strawberry.field(default=None)
    kind: enums.ActionKind = strawberry.field(description="The kind of the definition. This is the type of the definition. Can be either a function or a generator")
    is_test_for: list["str"] = strawberry.field(
        default_factory=list,
        description="The tests for the definition. This is used to group definitions together in the UI",
    )

    interfaces: list[str] = strawberry.field(
        default_factory=list,
        description="""The interfaces of the definition. This is used to group definitions together in the UI""",
    )
    is_dev: bool = strawberry.field(
        default=False,
        description="Whether the definition is a dev definition or not. If the definition is a dev definition, it can be used to create a dev action. If the definition is not a dev definition, it cannot be used to create a dev action",
    )
    logo: str | None = strawberry.field(
        default=None,
        description="The logo of the definition. This is used to display the logo in the UI",
    )


@pydantic.input(models.WindowInputModel, description="""A window that is calculated""")
class WindowInput:
    window_function: str
    label: str | None = None


@pydantic.input(models.TrackInputModel, description="""A value that is being tracked over time during the runtime of an action. This is the state of a dependency""")
class TrackInput:
    dependency_key: str | None = None
    state_key: str
    value_key: str
    label: str | None = None
    description: str | None = None
    windows: list[WindowInput] | None = None


@pydantic.input(
    models.ImplementationInputModel,
    description="""A implementation is a blueprint for a action. It is composed of a definition, a list of dependencies, and a list of params.""",
)
class ImplementationInput:
    definition: DefinitionInput
    interface: str | None = None
    instance_id: str | None = None
    params: scalars.AnyDefault | None = None
    dynamic: bool = False
    logo: str | None = None
    locks: list[str] | None = None
    optimistics: list[OptimisticInput] | None = None
    tracks: list[TrackInput] | None = None
    manipulates: list[str] | None = None
    needs_token: bool = True
    provenance_audience: list[str] | None = None
    effect: enums.EffectClass = enums.EffectClass.NONE
    dependencies: list[AgentDependencyInput] = strawberry.field(default_factory=list)


@pydantic.input(
    models.StateDefinitionInputModel,
    description="""A state schema is a blueprint for a state. It is composed of a definition, a list of dependencies, and a list of params.""",
)
class StateDefinitionInput:
    name: str
    ports: list[ReturnPortInput] = strawberry.field(default_factory=list)


@pydantic.input(
    models.StateImplementationInputModel,
    description="""A state implementation is a blueprint for a state. It is composed of a definition, a list of dependencies, and a list of params.""",
)
class StateImplementationInput:
    interface: str
    definition: StateDefinitionInput


@pydantic.input(
    models.LockDefinitionInputModel,
    description="Which locks does the agent provide in general",
)
class LockDefinitionInput:
    key: str
    description: str | None = None


@pydantic.input(
    models.LockImplementationInputModel,
    description="Which locks does the agent provide in general",
)
class LockImplementationInput:
    key: str
    definition: LockDefinitionInput


@pydantic.input(
    models.StructureInputModel,
    description="Which structures does the agent act upon in general",
)
class StructureInput:
    key: str
    description: str | None = None
    implements: list[str] | None = None
    descriptors: list[str] | None = None
    default_widget: Optional["AssignWidgetInput"] = None
    default_return_widget: Optional["ReturnWidgetInput"] = None
    qet_query: str | None = None
    describe_query: str | None = None


@pydantic.input(
    models.InterfaceInputModel,
    description="Which interfaces does the agent declare",
)
class InterfaceInput:
    key: str
    description: str | None = None
    default_widget: Optional["AssignWidgetInput"] = None
    default_return_widget: Optional["ReturnWidgetInput"] = None


@pydantic.input(models.DescriptorSchemaInputModel, description="A descriptor model")
class DescriptorSchemaInput:
    key: str
    description: str | None = None


@pydantic.input(
    models.StructurePackageInputModel,
    description="A structure schema model",
)
class StructurePackageInput:
    key: str
    version: str = "0.1.0"
    description: str | None = None
    descriptors: list[DescriptorSchemaInput] | None = None
    interfaces: list[InterfaceInput] | None = None
    structures: list[StructureInput] | None = None


@pydantic.input(models.DynamicValueInputModel, description="A bound state pointer referencing a variable inside a Blok state instance.")
class DynamicValueInput:
    path: Optional[str] = None


@pydantic.input(models.AgentCallInputModel, description="Defines a callback that routes user interactions directly to an Arkitekt Agent via Rekuest.")
class AgentCallInput:
    dependency: str
    operation: str
    arguments: Optional[List[Annotated["ActionArgumentInput", strawberry.lazy(__name__)]]] = None


@pydantic.input(models.UtilCallInputModel, description="Defines a utility call that can be invoked within the system.")
class UtilCallInput:
    operation: str
    arguments: Optional[List[Annotated["ActionArgumentInput", strawberry.lazy(__name__)]]] = None


@pydantic.input(models.ActionArgumentInputModel, description="A JSON-serializable argument entry for a multi-agent action trigger.")
class ActionArgumentInput:
    key: str | None = None
    value_literal: Optional[scalars.JSONSerializable] = None
    value_path: Optional[str] = None

    agent_call: Optional[AgentCallInput] = None
    util_call: Optional[UtilCallInput] = None
    value_list: Optional[List[Annotated["ActionArgumentInput", strawberry.lazy(__name__)]]] = None
    value_dict: Optional[List[Annotated["ActionArgumentInput", strawberry.lazy(__name__)]]] = None


@pydantic.input(models.ComponentPropInputModel, description="A single key-value prop configuration for a component layout node.")
class ComponentPropInput:
    key: str

    # Primitives mapping to standard properties, state paths, or actions
    static_value: Optional[scalars.JSONSerializable] = None
    dynamic_value: Optional[DynamicValueInput] = None
    agent_call: Optional[AgentCallInput] = None
    util_call: Optional[UtilCallInput] = None
    declares_value: Optional[str] = None


@pydantic.input(models.ComponentNodeInputModel, description="An abstract structural visual element inside a Blok blueprint manifest.")
class ComponentNodeInput:
    id: str
    component: str
    props: Optional[List[ComponentPropInput]] = strawberry.field(default_factory=list)
    children: Optional[List[Annotated["ComponentNodeInput", strawberry.lazy(__name__)]]] = None


@pydantic.input(
    models.BlokImplementationInputModel,
    description="Which locks does the agent provide in general",
)
class BlokImplementationInput:
    key: str
    dependencies: list[AgentDependencyInput] = strawberry.field(default_factory=list)
    components: list[ComponentNodeInput] = strawberry.field(default_factory=list)
    catalog: Optional[str] = None
    demo_state: Optional[scalars.JSONSerializable] = None
    description: Optional[str] = None
