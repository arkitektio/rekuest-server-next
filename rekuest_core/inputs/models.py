from typing import Any, List, Optional
from rekuest_core import enums
from pydantic import BaseModel, Field, model_validator
from typing_extensions import Self


class BindsInputModel(BaseModel):
    implementations: Optional[list[str]]
    clients: Optional[list[str]]
    desired_instances: int = 1
    minimum_instances: int = 1


class EffectDependencyInputModel(BaseModel):
    key: str
    condition: str
    value: str


class EffectInputModel(BaseModel):
    function: str
    dependencies: list[str] | None = []
    message: str | None = None
    kind: enums.EffectKind
    fade: bool = True
    hook: str | None = None
    ward: str | None = None


class ChoiceInputModel(BaseModel):
    value: str
    label: str
    image: str | None = None
    description: str | None = None


class ValidatorInputModel(BaseModel):
    function: str
    dependencies: list[str] | None = []
    label: str | None = None
    error_message: str | None = None


class StateAccessorInputModel(BaseModel):
    option_key: enums.OptionKey
    sub_path: str | None = None


class AssignWidgetInputModel(BaseModel):
    kind: enums.AssignWidgetKind
    query: str | None = None
    choices: list[ChoiceInputModel] | None = None
    state_choices: str | None = None
    follow_value: str | None = None
    min: float | None = None
    max: float | None = None
    step: float | None = None
    placeholder: str | None = None
    hook: str | None = None
    ward: str | None = None
    fallback: Optional["AssignWidgetInputModel"] = None
    filters: list["ArgPortInputModel"] | None = None
    dependencies: list[str] | None = []
    dependency: str | None = None
    target_dependency: str | None = None
    target_action: str | None = None
    target_port: str | None = None
    state_path: str | None = None
    state_accessors: list[StateAccessorInputModel] | None = None


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


class RequiresInputModel(BaseModel):
    key: str
    operator: enums.RequiresOperator
    value: Any


class ProvidesInputModel(BaseModel):
    key: str
    operator: enums.ProvidesOperator
    value: Any


class DescriptorSchemaInputModel(BaseModel):
    key: str
    description: str | None = None


class OptimisticInputModel(BaseModel):
    state: str
    path: str
    accessor: str | None = None


class PortInputModel(BaseModel):
    validators: list[ValidatorInputModel] | None = None
    key: str
    label: str | None = None
    kind: enums.PortKind
    description: str | None = None
    identifier: str | None = None
    nullable: bool = False
    effects: list[EffectInputModel] | None = None
    default: Any | None = None
    choices: list[ChoiceInputModel] | None = None

    @model_validator(mode="after")
    def check_children_for_port(self) -> Self:
        if self.kind == enums.PortKind.LIST and (self.children is None or len(self.children) != 1):
            raise ValueError("Port of kind LIST must have exactly on children")
        return self


class ArgPortInputModel(PortInputModel):
    default: Any | None = None
    widget: Optional["AssignWidgetInputModel"] = None
    requires: list[RequiresInputModel] | None = None
    children: Optional[list["ArgPortInputModel"]] = None

    @model_validator(mode="after")
    def check_children_for_port(self) -> Self:
        if self.kind == enums.PortKind.LIST and (self.children is None or len(self.children) != 1):
            raise ValueError("Port of kind LIST must have exactly on children")
        return self


class ReturnPortInputModel(PortInputModel):
    widget: Optional["ReturnWidgetInputModel"] = None
    provides: list[ProvidesInputModel] | None = None
    children: Optional[list["ReturnPortInputModel"]] = None

    @model_validator(mode="after")
    def check_children_for_port(self) -> Self:
        if self.kind == enums.PortKind.LIST and (self.children is None or len(self.children) != 1):
            raise ValueError("Port of kind LIST must have exactly on children")
        return self


class PortGroupInputModel(BaseModel):
    key: str
    title: str | None
    description: str | None
    effects: list[EffectInputModel] | None
    ports: list[str]


class PortMatchInputModel(BaseModel):
    at: int | None = None
    key: str | None = None
    kind: enums.PortKind | None = None
    identifier: str | None = None
    nullable: bool | None = None
    children: Optional[list["PortMatchInputModel"]] = None


class ActionDependencyInputModel(BaseModel):
    key: str
    version: str | None = None
    description: str | None = None
    action_key: str | None = None
    app: str | None = None
    arg_matches: list[PortMatchInputModel] | None = None
    return_matches: list[PortMatchInputModel] | None = None
    protocols: list[str] | None = None
    force_arg_length: int | None = None
    force_return_length: int | None = None
    optional: bool = False
    allow_inactive: bool = True


class StateDependencyInputModel(BaseModel):
    key: str
    version: str | None = None
    description: str | None = None
    state_key: str | None = None
    app: str | None = None
    port_matches: list[PortMatchInputModel] | None = None
    optional: bool = False
    allow_inactive: bool = True


class AgentDependencyInputModel(BaseModel):
    key: str
    app: str | None = None
    version: str | None = None

    description: str | None = None
    optional: bool = False

    # Filters for selecting which instances of the agent are valid for this dependency
    action_demands: list[ActionDependencyInputModel] | None = None
    state_demands: list[StateDependencyInputModel] | None = None
    auto_resolvable: bool = False

    min_viable_instances: int | None = None
    max_viable_instances: int | None = None
    prefered_instances: int | None = None
    assign_policy: enums.AssignPolicy = enums.AssignPolicy.BALANCED


class DefinitionInputModel(BaseModel):
    """A definition for a implementation"""

    key: str
    version: str = "1"
    description: str | None = None
    collections: list[str] = Field(default_factory=list)
    package: str | None = None
    name: str
    stateful: bool = False
    port_groups: list[PortGroupInputModel] = Field(default_factory=list)
    args: list[ArgPortInputModel] = Field(default_factory=list)
    returns: list[ReturnPortInputModel] = Field(default_factory=list)
    kind: enums.ActionKind
    tests: ActionDependencyInputModel | None = Field(default=None)
    is_test_for: list["str"] = Field(default_factory=list)
    interfaces: list[str] = Field(default_factory=list)
    is_dev: bool = False
    logo: str | None = None

    @model_validator(mode="after")
    def check_dependencies(self) -> Self:
        """Ensure that all dependencies in ports are valid."""
        all_arg_keys = [port.key for port in self.args]
        all_return_keys = [port.key for port in self.returns]

        for arg in self.args:
            for validator in arg.validators or []:
                if validator.dependencies:
                    for dep in validator.dependencies:
                        if dep not in all_arg_keys and dep not in all_return_keys:
                            raise ValueError(f"Validator {validator.label} in port {arg.key} has invalid dependency: {dep}")

            for effect in arg.effects or []:
                if effect.dependencies:
                    for dep in effect.dependencies:
                        if dep not in all_arg_keys and dep not in all_return_keys:
                            raise ValueError(f"Effect {effect.function} in port {arg.key} has invalid dependency: {dep}")

        return self


class DependencyInputModel(BaseModel):
    action: str
    hash: str
    reference: str | None
    binds: BindsInputModel | None
    optional: bool = False
    viable_instances: int | None


class WindowInputModel(BaseModel):
    window_function: str
    label: str | None = None


class TrackInputModel(BaseModel):
    dependency_key: str | None = None
    state_key: str
    value_key: str
    label: str | None = None
    description: str | None = None
    windows: list[WindowInputModel] | None = None


class ImplementationInputModel(BaseModel):
    definition: DefinitionInputModel
    dependencies: list[AgentDependencyInputModel] = Field(default_factory=list)
    tracks: list[TrackInputModel] | None = None
    interface: str
    params: dict[str, Any] | None = None
    instance_id: str | None = None
    dynamic: bool = False
    logo: str | None = None
    locks: list[str] | None = None
    manipulates: list[str] | None = None
    needs_token: bool = True
    provenance_audience: list[str] | None = None


class StateDefinitionInputModel(BaseModel):
    ports: list[ReturnPortInputModel]
    name: str


class StateImplementationInputModel(BaseModel):
    interface: str
    definition: StateDefinitionInputModel


class LockDefinitionInputModel(BaseModel):
    key: str
    description: str | None = None


class LockImplementationInputModel(BaseModel):
    key: str
    definition: LockDefinitionInputModel


class BlokImplementationInputModel(BaseModel):
    key: str
    definition: LockDefinitionInputModel


class InterfaceInputModel(BaseModel):
    key: str
    description: str | None = None
    default_widget: Optional[AssignWidgetInputModel] = None
    default_return_widget: Optional[ReturnWidgetInputModel] = None


class StructureInputModel(BaseModel):
    key: str
    description: str | None = None
    implements: list[str] = None
    descriptors: list[str] = None
    default_widget: Optional[AssignWidgetInputModel] = None
    default_return_widget: Optional[ReturnWidgetInputModel] = None
    qet_query: str | None = None
    describe_query: str | None = None


class StructurePackageInputModel(BaseModel):
    key: str
    version: str = "0.1.0"
    description: str | None = None
    interfaces: list[InterfaceInputModel] | None = None
    structures: list[StructureInputModel] | None = None
    descriptors: list[DescriptorSchemaInputModel] | None = None


class DynamicValueInputModel(BaseModel):
    """Base model for a dynamic value input, which can reference a variable in a Blok state instance.

    Attributes:
        literal: An optional static fallback literal value, passed as a serialized string or JSON primitive.
    """

    path: str | None = None


class AgentCallInputModel(BaseModel):
    """Base model for defining a callback that routes user interactions directly to an Arkitekt Agent via Rekuest.

    Attributes:
        target_dependency_key: The abstract agent dependency key declared in the Blok manifest (e.g., 'stage_dep').
        operation_name: The target function name registered on that specific agent's worker thread loop.
        arguments: An optional list of key-value arguments compiled for the target agent call.
    """

    dependency: str
    operation: str
    arguments: Optional[List["ActionArgumentInputModel"]] = None


class UtilCallInputModel(BaseModel):
    operation: str
    arguments: Optional[List["ActionArgumentInputModel"]] = None


class ActionArgumentInputModel(BaseModel):
    """Base model for an action argument input, which can be a static literal or a dynamic state reference.

    Attributes:
        key: The argument property name.
        value_literal: An optional static literal string value if not dynamically bound.
        value_path: An optional JSON Pointer referencing the shared Blok state to inject into this argument slot dynamically.
    """

    key: str | None = None
    value_literal: Optional[str | int | float | dict | list] = None
    value_path: Optional[str] = None

    # Separated nested calls
    agent_call: Optional["AgentCallInputModel"] = None
    util_call: Optional["UtilCallInputModel"] = None

    value_list: Optional[List["ActionArgumentInputModel"]] = None
    value_dict: Optional[List["ActionArgumentInputModel"]] = None


# ============================================================================
# 2. Abstract Component Property Bindings
# ============================================================================
class ComponentPropInputModel(BaseModel):
    """Base model for a single key-value prop configuration for a component layout node.

    Attributes:
        key: The prop key name matching the target UI catalog constraint.
        static_value: An optional raw scalar or JSON-stringified literal configuration parameter (e.g., '40x' or True).
        dynamic_value: An optional reactive state data-binding rule.
        agent_action: An optional imperative interactive network action callback loop.
    """

    key: str
    static_value: Optional[str | int | float | dict] = None
    dynamic_value: Optional[DynamicValueInputModel] = None
    declares_value: Optional[str] = None  # For declaring a new variable in the Blok state from this prop's value

    # Separated top-level callbacks
    agent_call: Optional["AgentCallInputModel"] = None
    util_call: Optional["UtilCallInputModel"] = None


# 3. The Unified Abstract Component Node Input
# ============================================================================
class ComponentNodeInputModel(BaseModel):
    """Base model for an abstract structural visual element inside a Blok blueprint manifest.

    Attributes:
        id: Unique structural string identifying this node instance inside the flat workspace layout tree.
        component: The type indicator token matching your Electron app's registered catalog specs (e.g. 'Slider').
        props: The collection of static values, state pointers, or action endpoints assigned to this component.
        children: Flat adjacency pointer list mapping out IDs nested inside this specific component layer.
    """

    id: str
    component: str
    props: list[ComponentPropInputModel] | None = None
    children: list["ComponentNodeInputModel"] | None = None


class BlokImplementationInputModel(BaseModel):
    "Base model for a Blok implementation manifest, which compiles all necessary information to materialize a Blok instance in the Arkitekt ecosystem."

    key: str
    dependencies: list[AgentDependencyInputModel] = Field(default_factory=list, description="The dependencies required by this Blok.")
    components: list[ComponentNodeInputModel]
    catalog: Optional[str] = None
    description: Optional[str] = None
    demo_state: Optional[dict] = None


AssignWidgetInputModel.model_rebuild()
