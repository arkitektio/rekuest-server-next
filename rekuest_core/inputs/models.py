import hashlib
import json
from typing import Any, List, Optional
from rekuest_core import enums, units
from pydantic import BaseModel, Field, model_validator
from typing_extensions import Self


class BindsInputModel(BaseModel):
    implementations: Optional[list[str]] = Field(description="The implementations (by id) that are allowed to fulfill this bind. If None, any implementation is allowed.")
    clients: Optional[list[str]] = Field(description="The clients (by id) that are allowed to fulfill this bind. If None, any client is allowed.")
    desired_instances: int = Field(default=1, description="The desired number of instances that should fulfill this bind.")
    minimum_instances: int = Field(default=1, description="The minimum number of instances that must fulfill this bind for it to be viable.")


class EffectDependencyInputModel(BaseModel):
    key: str = Field(description="The key of the port this effect dependency refers to.")
    condition: str = Field(description="The condition operator to evaluate against the referenced port's value.")
    value: str = Field(description="The value to compare the referenced port's value against.")


class EffectInputModel(BaseModel):
    function: str = Field(description="The function to run to determine if the effect should be applied")
    dependencies: list[str] | None = Field(
        default_factory=list,
        description="The dependencies of the effect. Use the .. syntax to traverse the tree of ports. For example, if you have a port with the key 'foo' and you want to reference a port with the key 'bar' that is a child of 'foo', you would use 'foo..bar'",
    )
    message: str | None = Field(default=None, description="The message to display when the effect is applied (if it is a message effect)")
    kind: enums.EffectKind = Field(description="The kind of the effect. Can be either message, hide or custom")
    fade: bool = Field(default=True, description="Whether to fade out the port when the effect is applied (if it is a hide effect)")
    hook: str | None = Field(default=None, description="The hook to run when the effect is applied (if it is a custom effect)")
    ward: str | None = Field(default=None, description="The ward to run when the effect is applied (if it is a custom effect)")


class ChoiceInputModel(BaseModel):
    value: str = Field(description="The value of the choice. This is the value that is returned when the choice is selected")
    label: str = Field(description="The label of the choice. This is the text that is displayed in the UI")
    image: str | None = Field(default=None, description="The image of the choice. This is the image that is displayed in the UI (must be a URL)")
    description: str | None = Field(default=None, description="The description of the choice. This is the text that is displayed in the UI when the user hovers over the choice")


class ValidatorInputModel(BaseModel):
    function: str = Field(description="The function to run when validating the port")
    dependencies: list[str] | None = Field(
        default_factory=list,
        description="The dependencies of the function. Use the .. syntax to traverse the tree of ports. For example, if you have a port with the key 'foo' and you want to reference a port with the key 'bar' that is a child of 'foo', you would use 'foo..bar'",
    )
    label: str | None = Field(default=None, description="An optional human-readable label for the validator.")
    error_message: str | None = Field(default=None, description="The error message to display when the validation fails")


class StateAccessorInputModel(BaseModel):
    option_key: enums.OptionKey = Field(description="The part of the state accessor to use as the value for the assign widget (e.g. the key, the description, the logo, etc.)")
    sub_path: str | None = Field(
        default=None,
        description="The sub path to access a specific part of the state value. Always traverse from top to bottom level. i.e state.x for state.x and state.x.y for state.x.y. You can also use an arrow function to specify a dynamic path based on the other arguments, e.g. (args) => state[args.foo]",
    )


class AssignWidgetInputModel(BaseModel):
    kind: enums.AssignWidgetKind = Field(description="The kind of the assign widget. Can be either dropdown, text, slider, checkbox, radio or custom")
    query: str | None = Field(default=None, description="The query to run when searching for choices. This is used for dropdowns and text inputs")
    choices: list[ChoiceInputModel] | None = Field(default=None, description="The choices to display in the dropdown. This is used for dropdowns and text inputs")
    state_choices: str | None = Field(default=None, description="The key of a state whose value provides the choices for this widget (state-driven choices).")
    follow_value: str | None = Field(default=None, description="The key of another port whose value this widget should follow and mirror.")
    min: float | None = Field(default=None, description="The minimum value of the slider (if a slider). This is used for sliders and text inputs")
    max: float | None = Field(default=None, description="The maximum value of the slider (if a slider). This is used for sliders and text inputs")
    step: float | None = Field(default=None, description="The step value of the slider (if a slider). This is used for sliders and text inputs")
    placeholder: str | None = Field(default=None, description="The placeholder of the input. This is used for text inputs and dropdowns")
    as_paragraph: bool | None = Field(default=None, description="Whether to display the input as a paragraph or not. This is used for text inputs and dropdowns")
    hook: str | None = Field(default=None, description="The hook to run when the input is changed. This is used for custom assign widgets")
    ward: str | None = Field(default=None, description="The ward that is responsible for handling querying the choices")
    fallback: Optional["AssignWidgetInputModel"] = Field(default=None, description="The fallback assign widget to use if the current one fails. This is used for custom assign widgets")
    filters: list["ArgPortInputModel"] | None = Field(default=None, description="The filters to apply to a search widget. This is used for custom assign widgets")
    dependencies: list[str] | None = Field(
        default_factory=list,
        description="The dependencies of the assign widget, which will be passed to the search or the hook widget. Use the .. syntax to traverse the tree of ports. For example, if you have a port with the key 'foo' and you want to reference a port with the key 'bar' that is a child of 'foo', you would use 'foo..bar'",
    )
    dependency: str | None = Field(default=None, description="The dependency that we are going to use to fullfill the state choices. If none is provided its the own state that will be queried")
    target_dependency: str | None = Field(default=None, description="The dependency that we are going to target with a proxy widget. This is used for proxy widgets")
    target_action: str | None = Field(default=None, description="The action that we are going to target with a proxy widget. This is used for proxy widgets")
    target_port: str | None = Field(default=None, description="The port that we are going to target with a proxy widget. This is used for proxy widgets")
    state_path: str | None = Field(
        default=None,
        description="The path to the state value that we are going to use to fullfill the state choices. Always traverse from top to bottom level. i.e state.x for state.x and state.x.y for state.x.y. You can also use an arrow function to specify a dynamic path based on the other arguments, e.g. (args) => state[args.foo]",
    )
    state_accessors: list[StateAccessorInputModel] | None = Field(
        default=None,
        description="State accessors are used to specify how to access the state values that we are going to use to fullfill the state choices. This is used when the state value that we want to use is not the same as the one of the port, e.g. when we want to use a specific key of a state object, or when we want to use a dynamic key based on the other arguments. The option_key field is used to specify which part of the state accessor we want to use as the value for the assign widget (e.g. the key, the description, the logo, etc.)",
    )


class ReturnWidgetInputModel(BaseModel):
    kind: enums.ReturnWidgetKind = Field(description="The kind of the return widget. Can be either dropdown, text, slider, checkbox, radio or custom")
    query: str | None = Field(default=None, description="The query to run when searching for choices. This is used for dropdowns and text inputs")
    choices: list[ChoiceInputModel] | None = Field(default=None, description="The choices to display in the dropdown. This is used for dropdowns and text inputs")
    min: int | None = Field(default=None, description="The minimum value to display (if a slider).")
    max: int | None = Field(default=None, description="The maximum value to display (if a slider).")
    step: int | None = Field(default=None, description="The step value to display (if a slider).")
    placeholder: str | None = Field(default=None, description="The placeholder text of the return widget.")
    hook: str | None = Field(default=None, description="The hook to run (if it is a custom return widget).")
    ward: str | None = Field(default=None, description="The ward responsible for handling the return widget.")


class RequiresInputModel(BaseModel):
    key: str = Field(description="The key of the requirement. This is used to uniquely identify the requirement")
    operator: enums.RequiresOperator = Field(description="The operator for the requirement")
    value: Any = Field(description="The value of the requirement. This can be any JSON serializable value")


class ProvidesInputModel(BaseModel):
    key: str = Field(description="The key of the provision. This is used to uniquely identify the provision")
    operator: enums.ProvidesOperator = Field(description="The operator for the provision")
    value: Any = Field(description="The value of the provision. This can be any JSON serializable value")


class OptimisticInputModel(BaseModel):
    state: str = Field(description="The state to optimistically set when the action is assigned")
    path: str = Field(
        description="The path to the state.value to optimistically set the value, always traverse from top to bottom level. i.e state.x for state.x and state.x.y for state.x.y. You can also use an arrow function to specify a dynamic path based on the other arguments, e.g. (args) => state[args.foo]"
    )
    accessor: str | None = Field(default=None, description="The accessor to get the value to optimistically set. This is used when the value to optimistically set is not the same as the value of the port")


class PortInputModel(BaseModel):
    validators: list[ValidatorInputModel] | None = Field(default=None, description="The validators for the port")
    key: str = Field(description="The key of the port")
    label: str | None = Field(default=None, description="The label of the port. This is the text that is displayed in the UI")
    kind: enums.PortKind = Field(description="The kind of the port. This is the type of the port. Can be either int, string, structure, list, bool, dict, float, date, union or model")
    description: str | None = Field(default=None, description="The description of the port. This is the text that is displayed in the UI when the user hovers over the port")
    identifier: str | None = Field(default=None, description="The identifier of a structure port. This is used to uniquely identify a specific type of structure.")
    nullable: bool = Field(default=False, description="Whether the port is nullable or not. If the port is nullable, it can be set to null. If the port is not nullable, it cannot be set to null")
    effects: list[EffectInputModel] | None = Field(default=None, description="The effects of the port")
    default: Any | None = Field(default=None, description="The default value for the port.")
    choices: list[ChoiceInputModel] | None = Field(default=None, description="The options for the port. This is used for dropdowns and text inputs")
    reference_unit: str | None = Field(default=None, description="For QUANTITY ports: the canonical/reference unit of the physical quantity, e.g. \"volt\" or \"farad\". It is the default selection and the key used to resolve the concrete quantity type; other units of the same dimension are still allowed.")
    proposed_units: list[str] | None = Field(default=None, description="For QUANTITY ports: units offered as a dropdown in the UI, e.g. [\"pF\", \"nF\", \"uF\"]. Proposals only — any unit of the same dimension remains valid input.")
    dimension: str | None = Field(default=None, description="For QUANTITY ports: the pint dimensionality string, e.g. \"[mass] * [length] ** 2 / [time] ** 3 / [current]\". This is the wiring-compatibility key between quantity ports.")
    children: Optional[list["PortInputModel"]] = Field(default=None, description="The child ports (used for list, dict, union and model ports).")

    @model_validator(mode="after")
    def check_kind_specific_fields(self) -> Self:
        if self.kind == enums.PortKind.LIST and (self.children is None or len(self.children) != 1):
            raise ValueError("Port of kind LIST must have exactly one child")

        if self.kind == enums.PortKind.QUANTITY:
            if not self.reference_unit:
                raise ValueError(f"QUANTITY port '{self.key}' must declare a reference_unit")
            derived = units.dimensionality_of(self.reference_unit)
            if self.dimension is not None and units.dimensionality_of(self.dimension) != derived:
                raise ValueError(f"QUANTITY port '{self.key}': dimension '{self.dimension}' is inconsistent with reference_unit '{self.reference_unit}' (dimensionality '{derived}')")
            self.dimension = derived  # derive or canonicalize the wiring-compatibility key
            for unit in self.proposed_units or []:
                unit_dim = units.dimensionality_of(unit)
                if unit_dim != derived:
                    raise ValueError(f"QUANTITY port '{self.key}': proposed unit '{unit}' has dimensionality '{unit_dim}', expected '{derived}'")
        else:
            offending = [f for f in ("reference_unit", "proposed_units", "dimension") if getattr(self, f) is not None]
            if offending:
                raise ValueError(f"Port '{self.key}' of kind {self.kind.value} must not set QUANTITY-only fields: {', '.join(offending)}")
        return self


class ArgPortInputModel(PortInputModel):
    default: Any | None = Field(default=None, description="The default value for the port.")
    widget: Optional["AssignWidgetInputModel"] = Field(default=None, description="The assign widget to use for this port.")
    requires: list[RequiresInputModel] | None = Field(default=None, description="The descriptors for the port. Descriptors are key-value pairs that can be used to add additional metadata to a port. When using rekuest's action search, you can filter actions based on their port descriptors")
    children: Optional[list["ArgPortInputModel"]] = Field(default=None, description="The child ports (used for list, dict, union and model ports).")


class ReturnPortInputModel(PortInputModel):
    widget: Optional["ReturnWidgetInputModel"] = Field(default=None, description="The return widget to use for this port.")
    provides: list[ProvidesInputModel] | None = Field(default=None, description="The provisions for the port. Provisions are key-value pairs that can be used to add additional metadata to a port. When using rekuest's action search, you can filter actions based on their port provisions")
    children: Optional[list["ReturnPortInputModel"]] = Field(default=None, description="The child ports (used for list, dict, union and model ports).")


class PortGroupInputModel(BaseModel):
    key: str = Field(description="The key of the port group. This is used to uniquely identify the port group")
    title: str | None = Field(description="The title of the port group. This is the text that is displayed in the UI")
    description: str | None = Field(description="The description of the port group. This is the text that is displayed in the UI")
    effects: list[EffectInputModel] | None = Field(description="The effects applied to the port group as a whole.")
    ports: list[str] = Field(description="The keys of the ports that belong to this group.")


class DescriptorInputModel(BaseModel):
    key: str = Field(description="The descriptor key, e.g. 'axes'.")
    value: Any = Field(description="The descriptor value. Any JSON-serializable value.")


class PortMatchInputModel(BaseModel):
    at: int | None = Field(default=None, description="The index of the port to match.")
    key: str | None = Field(default=None, description="The key of the port to match.")
    kind: enums.PortKind | None = Field(default=None, description="The kind of the port to match.")
    identifier: str | None = Field(default=None, description="The identifier of the port to match.")
    nullable: bool | None = Field(default=None, description="Whether the port is nullable.")
    dimension: str | None = Field(default=None, description="The canonical pint dimensionality the port must have (QUANTITY wiring-compatibility key).")
    descriptors: list[DescriptorInputModel] | None = Field(default=None, description="Runtime descriptors of a candidate object, evaluated against the port's compiled requires micro-constraint. Omit for purely structural matching.")
    children: Optional[list["PortMatchInputModel"]] = Field(default=None, description="The matches for the children of the port to match.")


class ActionDemandInputModel(BaseModel):
    """Pure matching criteria for an action — the single demand shape used by query filters
    and (wrapped in a dependency) by dependency declarations.

    The preferred identification is ``app`` + ``key`` (e.g. "imagej" / "open_image"); the
    structural matches describe what the action must look like, so a resolver (or the user,
    when assigning) can progressively loosen the demand to equivalent actions of other apps.
    """

    hash: str | None = Field(default=None, description="The exact hash of the action. When set, matching short-circuits on the hash and everything else is ignored.")
    key: str | None = Field(default=None, description="The action's key within its app, e.g. 'open_image'. Together with `app` this is the preferred identification of the demanded action.")
    app: str | None = Field(default=None, description="The identifier of the app providing the action, e.g. 'imagej'. Omit (or drop when loosening) to allow equivalent actions from any app.")
    version: str | None = Field(default=None, description="The exact version of the action.")
    name: str | None = Field(default=None, description="The display name of the action to match.")
    arg_matches: list[PortMatchInputModel] | None = Field(default=None, description="The matches the action's arg ports must satisfy.")
    return_matches: list[PortMatchInputModel] | None = Field(default=None, description="The matches the action's return ports must satisfy.")
    protocols: list[str] | None = Field(default=None, description="Protocols (by name) the action must implement, e.g. 'predicate'.")
    force_arg_length: int | None = Field(default=None, description="Require that the action has exactly this number of root args.")
    force_return_length: int | None = Field(default=None, description="Require that the action has exactly this number of root returns.")
    pure: bool | None = Field(default=None, description="Require the action to be (or not be) pure. Omit to match either.")
    idempotent: bool | None = Field(default=None, description="Require the action to be (or not be) idempotent. Omit to match either.")
    stateful: bool | None = Field(default=None, description="Require the action to be (or not be) stateful. Omit to match either.")


class StateDemandInputModel(BaseModel):
    """Pure matching criteria for a state — the single state demand shape.

    The preferred identification is ``app`` + ``key`` (matched against the State's own
    identity columns); the structural ``matches`` on the state definition's ports loosen
    the demand to equivalent states of other apps.
    """

    hash: str | None = Field(default=None, description="The exact hash of the state definition. When set, matching short-circuits on the hash.")
    key: str | None = Field(default=None, description="The state's identity key on the agent (defaults to the interface at registration).")
    app: str | None = Field(default=None, description="The identifier of the app providing the state.")
    matches: list[PortMatchInputModel] | None = Field(default=None, description="The matches the state definition's ports must satisfy.")
    protocols: list[str] | None = Field(default=None, description="Protocols (by name) the state must implement.")


class ActionDependencyInputModel(BaseModel):
    """A named action requirement of a dependency: a local slot ``key`` mapped to the
    ``demand`` the resolved action must satisfy."""

    key: str = Field(description="The local slot key of this action requirement — callers reference it when assigning.")
    description: str | None = Field(default=None, description="The description of the dependency, why it is needed and what it is used for.")
    demand: ActionDemandInputModel | None = Field(default=None, description="The matching criteria the resolved action must satisfy (app/key preferred; matches loosen).")
    optional: bool = Field(default=False, description="Whether the dependency is optional or not. If the dependency is optional, the agent doesn't have to provide it to be potentially callable")
    allow_inactive: bool = Field(default=True, description="Allow inactive nodes, defaults to true")


class StateDependencyInputModel(BaseModel):
    """A named state requirement of a dependency: a local slot ``key`` mapped to the
    ``demand`` the agent's state must satisfy."""

    key: str = Field(description="The local slot key of this state requirement — callers reference it when assigning.")
    description: str | None = Field(default=None, description="The description of the dependency, why it is needed and what it is used for.")
    demand: StateDemandInputModel | None = Field(default=None, description="The matching criteria the agent's state must satisfy (app/key preferred; matches loosen).")
    optional: bool = Field(default=False, description="Whether the dependency is optional or not. If the dependency is optional, the agent doesn't have to provide it to be potentially callable")
    allow_inactive: bool = Field(default=True, description="Allow inactive nodes, defaults to true")


class AgentDependencyInputModel(BaseModel):
    key: str = Field(description="The key of this dependency, when assigning you can reference this key to specify which agent_dependency you are assigning to.")
    app: str | None = Field(
        default=None,
        description="Which app this dependency corresponds to (i.e. do you want to use a stardist agent for that or imagej agents needs to be a world unique classsifier (reverse domain notation) that identifies the type of agent you want to use, and then we can have multiple agents of the same type running in the system, e.g. startdist could be the app for all agents that correpsond to a startdist instance)",
    )
    version: str | None = Field(default=None, description="The version of the app this dependency corresponds to.")

    name: str | None = Field(default=None, description="The name of the agent. This is used to identify the agent in the system.")
    description: str | None = Field(default=None, description="A description of the dependency, why it is needed and what it is used for. This can be used to provide more context to users when assigning dependencies.")
    optional: bool = Field(default=False, description="Whether the dependency is optional or not. If the dependency is optional, users can choose to not provide it")

    # Filters for selecting which instances of the agent are valid for this dependency
    action_dependencies: list[ActionDependencyInputModel] | None = Field(default=None, description="The named action requirements of the agent — each a slot key plus the demand the resolved action must satisfy.")
    state_dependencies: list[StateDependencyInputModel] | None = Field(default=None, description="The named state requirements of the agent — each a slot key plus the demand the agent's state must satisfy.")
    auto_resolvable: bool = Field(
        default=False,
        description="Whether this dependency is auto resolvable or not. If so we will try to automatically resolve it based on the demands specified in the dependency and the capabilities of the available agents in the system. This is used to identify the demand in the system. Attention if any of the dependencies of this agent dependency is not auto resolvable, this dependency will also not be auto resolvable",
    )

    mutually_exclusive_keys: list[str] | None = Field(
        default=None, description="A list of keys of other agent dependencies that are mutually exclusive with this one. This means two agent dependencies with mutually exclusive keys cannot be assigned to the same implementing agent. This is used to identify the demand in the system."
    )
    min_viable_instances: int | None = Field(default=None, description="The minimum amount of viable instances for the agent. This is used to identify the demand in the system.")
    max_viable_instances: int | None = Field(default=None, description="The maximum amount of viable instances for the agent. This is used to identify the demand in the system.")
    prefered_instances: int | None = Field(default=None, description="The prefered amount of instances for the agent. This is used to identify the demand in the system.")
    assign_policy: enums.AssignPolicy = Field(default=enums.AssignPolicy.BALANCED, description="The policy used to pick which instance of the agent to assign to.")


class DefinitionInputModel(BaseModel):
    """A definition for a implementation"""

    key: str = Field(description="The key of the definition. This is used to uniquely identify the definition")
    version: str = Field(default="1", description="The version of the definition. This is used to differentiate if the underyling algorithm has changed, i.e we would expect different results for the same input")
    description: str | None = Field(default=None, description="The description of the definition. This is the text that is displayed in the UI")
    collections: list[str] = Field(default_factory=list, description="The collections of the definition. This is used to group definitions together in the UI")
    package: str | None = Field(default=None, description="The package of the function. Will default to the currents agent's app if not specified. This is used to group definitions together in the UI and provide a better user experience")
    name: str = Field(description="The name of the actions. This is used to uniquely identify the definition")
    stateful: bool = Field(default=False, description="Whether the definition is stateful or not. If the definition is stateful, it can be used to create a stateful action. If the definition is not stateful, it cannot be used to create a stateful action")
    pure: bool = Field(default=False, description="Whether the action is pure: same args always produce the same result and no side effects — its results are replayable/cacheable. Implies idempotent. Incompatible with stateful and with a PHYSICAL effect class.")
    idempotent: bool = Field(default=False, description="Whether the action is idempotent: safe to run multiple times with the same args without changing the outcome — on ambiguous executor loss it may be freely re-dispatched.")
    port_groups: list[PortGroupInputModel] = Field(default_factory=list, description="The port groups of the definition. This is used to group ports together in the UI")
    args: list[ArgPortInputModel] = Field(default_factory=list, description="The args of the definition. This is the input ports of the definition")
    returns: list[ReturnPortInputModel] = Field(default_factory=list, description="The returns of the definition. This is the output ports of the definition")
    kind: enums.ActionKind = Field(description="The kind of the definition. This is the type of the definition. Can be either a function or a generator")
    tests: ActionDependencyInputModel | None = Field(default=None, description="The test dependency for the definition.")
    is_test_for: list["str"] = Field(default_factory=list, description="The actions this definition is a test for. This is used to group definitions together in the UI")
    interfaces: list[str] = Field(default_factory=list, description="The interfaces of the definition. This is used to group definitions together in the UI")
    is_dev: bool = Field(default=False, description="Whether the definition is a dev definition or not. If the definition is a dev definition, it can be used to create a dev action. If the definition is not a dev definition, it cannot be used to create a dev action")
    logo: str | None = Field(default=None, description="The logo of the definition. This is used to display the logo in the UI")

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

    @property
    def unique_hash(self) -> str:
        """Stable sha256 over the identity-bearing subset of the definition (stored as Action.hash)."""
        hashable_definition = {
            key: value
            for key, value in dict(self.model_dump()).items()
            if key
            in [
                "name",
                "description",
                "args",
                "returns",
                "stateful",
                "is_test_for",
                "collections",
                "dependencies",
                "key",
                "version",
            ]
        }
        return hashlib.sha256(json.dumps(hashable_definition, sort_keys=True).encode()).hexdigest()


class DependencyInputModel(BaseModel):
    action: str = Field(description="The action (by hash) this dependency points to.")
    hash: str = Field(description="The hash of the action this dependency points to.")
    reference: str | None = Field(description="An optional reference used to identify this dependency within its graph.")
    binds: BindsInputModel | None = Field(description="The binds that constrain which implementations and clients may fulfill this dependency.")
    optional: bool = Field(default=False, description="Whether the dependency is optional or not.")
    viable_instances: int | None = Field(description="The number of viable instances required for this dependency.")


class WindowInputModel(BaseModel):
    window_function: str = Field(description="The window function to apply over the tracked value.")
    label: str | None = Field(default=None, description="An optional human-readable label for the window.")


class TrackInputModel(BaseModel):
    dependency_key: str | None = Field(default=None, description="The key of the dependency whose state is being tracked.")
    state_key: str = Field(description="The key of the state to track.")
    value_key: str = Field(description="The key of the value within the state to track.")
    label: str | None = Field(default=None, description="An optional human-readable label for the track.")
    description: str | None = Field(default=None, description="An optional description for the track.")
    windows: list[WindowInputModel] | None = Field(default=None, description="The windows (aggregations) computed over the tracked value.")


class ImplementationInputModel(BaseModel):
    definition: DefinitionInputModel = Field(description="The definition of the implementation. This is used to uniquely identify the implementation")
    dependencies: list[AgentDependencyInputModel] = Field(default_factory=list, description="The agent dependencies required by this implementation.")
    tracks: list[TrackInputModel] | None = Field(default=None, description="The tracks of the definition. This is used to track values over time during the runtime of an action. This is the state of a dependency")
    interface: str = Field(description="The interface of the implementation. This is used to group implementations together in the UI")
    params: dict[str, Any] | None = Field(default=None, description="The params of the implementation. This is used to pass parameters to the implementation")
    instance_id: str | None = Field(default=None, description="The instance id of the agent this implementation is bound to.")
    dynamic: bool = Field(default=False, description="Whether the implementation is dynamic or not. If the implementation is dynamic, it can be used to create a dynamic action. If the implementation is not dynamic, it cannot be used to create a dynamic action")
    logo: str | None = Field(default=None, description="The logo of the implementation. This is used to display the logo in the UI either it should be 'custom:svg-paths' or a lucide icon name like 'lucide:activity' urls are not supported at the moment")
    locks: list[str] | None = Field(default=None, description="The locks of the implementation. This is used to specify which resources the implementation needs to run")
    optimistics: list[OptimisticInputModel] | None = Field(default=None, description="The optimistics of the definition. This is used to optimistically set state values when the action is assigned, to provide a better user experience.")
    manipulates: list[str] | None = Field(default=None, description="The states that the implementation manipulates. This is used to identify which states are manipulated by the implementation, and can be use to enhance state safety in the system")
    needs_token: bool = Field(default=True, description="Whether Rekuest should mint a signed provenance token when this implementation is assigned. Default true (provenance-by-default); set false for trivial/internal tasks that never produce external provenance.")
    provenance_audience: list[str] | None = Field(default=None, description="The downstream service(s) the provenance token should be scoped to (the token's `aud`). If omitted, Rekuest derives the audience from the structures the assignment acts on.")
    effect: enums.EffectClass = Field(
        default=enums.EffectClass.NONE, description="The effect class of this implementation. NONE work is freely retryable/reclaimable; PHYSICAL work touches the real world and an ambiguous failure is terminal (never retried). Declared by the implementation here — never by the caller."
    )


class StateDefinitionInputModel(BaseModel):
    ports: list[ReturnPortInputModel] = Field(description="The ports of the state schema. This is used to define the structure of the state")
    name: str = Field(description="The name of the state schema. This is used to uniquely identify the state schema")


class StateImplementationInputModel(BaseModel):
    interface: str = Field(description="The key of the state implementation. This is used to uniquely identify the state implementation")
    key: str | None = Field(default=None, description="The stable identity key of the state, matched by state demands. Defaults to the interface when omitted.")
    app: str | None = Field(default=None, description="The identifier of the app providing this state. Defaults to the registering agent's app identifier when omitted.")
    definition: StateDefinitionInputModel = Field(description="The schema of the state implementation. This is used to define the structure of the state")


class LockDefinitionInputModel(BaseModel):
    key: str = Field(description="The key of the lock. This is used to uniquely identify the lock")
    description: str | None = Field(default=None, description="Describe the lock a bit")


class LockImplementationInputModel(BaseModel):
    key: str = Field(description="The key of the lock implementation.")
    definition: LockDefinitionInputModel = Field(description="The lock definition this implementation fulfills.")


class BlokImplementationInputModel(BaseModel):
    key: str = Field(description="The key of the blok implementation.")
    definition: LockDefinitionInputModel = Field(description="The definition this blok implementation fulfills.")


class InterfaceInputModel(BaseModel):
    key: str = Field(description="The key of the interface. This is used to uniquely identify the interface")
    description: str | None = Field(default=None, description="Describe the interface a bit")
    default_widget: Optional[AssignWidgetInputModel] = Field(default=None, description="The default assign widget for ports implementing this interface.")
    default_return_widget: Optional[ReturnWidgetInputModel] = Field(default=None, description="The default return widget for ports implementing this interface.")


class StructureInputModel(BaseModel):
    key: str = Field(description="The key of the structure. This is used to uniquely identify the structure")
    description: str | None = Field(default=None, description="Describe the structure a bit")
    implements: list[str] = Field(default=None, description="The interfaces this structure implements.")
    descriptors: list[str] = Field(default=None, description="The descriptors that annotate this structure.")
    default_widget: Optional[AssignWidgetInputModel] = Field(default=None, description="The default assign widget for ports of this structure.")
    default_return_widget: Optional[ReturnWidgetInputModel] = Field(default=None, description="The default return widget for ports of this structure.")
    qet_query: str | None = Field(default=None, description="The query used to get a single instance of this structure.")
    describe_query: str | None = Field(default=None, description="The query used to describe and search instances of this structure.")


class DynamicValueInputModel(BaseModel):
    """Base model for a dynamic value input, which can reference a variable in a Blok state instance.

    Attributes:
        literal: An optional static fallback literal value, passed as a serialized string or JSON primitive.
    """

    path: str | None = Field(default=None, description="JSON Pointer to a variable inside the Blok's isolated data model (e.g., '/microscope/exposure').")


class AgentCallInputModel(BaseModel):
    """Base model for defining a callback that routes user interactions directly to an Arkitekt Agent via Rekuest.

    Attributes:
        target_dependency_key: The abstract agent dependency key declared in the Blok manifest (e.g., 'stage_dep').
        operation_name: The target function name registered on that specific agent's worker thread loop.
        arguments: An optional list of key-value arguments compiled for the target agent call.
    """

    dependency: str = Field(description="The abstract agent dependency key declared in the Blok manifest (e.g., 'stage_dep').")
    operation: str = Field(description="The target function name registered on that specific agent's worker thread loop.")
    arguments: Optional[List["ActionArgumentInputModel"]] = Field(default=None, description="Key-value arguments map compiled for the target agent call.")


class UtilCallInputModel(BaseModel):
    operation: str = Field(description="The utility function name to invoke.")
    arguments: Optional[List["ActionArgumentInputModel"]] = Field(default=None, description="Key-value arguments map compiled for the target utility call.")


class ActionArgumentInputModel(BaseModel):
    """Base model for an action argument input, which can be a static literal or a dynamic state reference.

    Attributes:
        key: The argument property name.
        value_literal: An optional static literal string value if not dynamically bound.
        value_path: An optional JSON Pointer referencing the shared Blok state to inject into this argument slot dynamically.
    """

    key: str | None = Field(default=None, description="The argument property name.")
    value_literal: Optional[str | int | float | dict | list] = Field(default=None, description="Static literal value if not dynamically bound.")
    value_path: Optional[str] = Field(default=None, description="JSON Pointer referencing the shared Blok state to inject into this argument slot dynamically.")

    # Separated nested calls
    agent_call: Optional["AgentCallInputModel"] = Field(default=None, description="Defines a nested agent call if this argument should trigger an agent interaction.")
    util_call: Optional["UtilCallInputModel"] = Field(default=None, description="Defines a nested utility call if this argument should trigger a system utility interaction.")

    value_list: Optional[List["ActionArgumentInputModel"]] = Field(default=None, description="Defines a list of values if this argument should be an array.")
    value_dict: Optional[List["ActionArgumentInputModel"]] = Field(default=None, description="Defines a list of key-value pairs if this argument should be a dictionary.")


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

    key: str = Field(description="The prop key name matching the target UI catalog constraint.")
    static_value: Optional[str | int | float | dict] = Field(default=None, description="A raw scalar or JSON-stringified literal configuration parameter (e.g. '40x' or True).")
    dynamic_value: Optional[DynamicValueInputModel] = Field(default=None, description="A reactive state data-binding rule.")
    declares_value: Optional[str] = Field(default=None, description="If set, this prop declares a new 'value' in the Blok state that can be referenced by other props or actions. The value of this field should be the name of the declared value (e.g., 'selected_user').")

    # Separated top-level callbacks
    agent_call: Optional["AgentCallInputModel"] = Field(default=None, description="Defines an imperative interactive network action callback loop if this prop should trigger an agent interaction.")
    util_call: Optional["UtilCallInputModel"] = Field(default=None, description="Defines an imperative interactive network action callback loop if this prop should trigger a system utility interaction.")


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

    id: str = Field(description="Unique structural string identifying this node instance inside the flat workspace layout tree.")
    component: str = Field(description="The type indicator token matching your Electron app's registered catalog specs (e.g. 'Slider').")
    props: list[ComponentPropInputModel] | None = Field(default=None, description="The collection of static values, state pointers, or action endpoints assigned to this component.")
    children: list["ComponentNodeInputModel"] | None = Field(default=None, description="Flat adjacency pointer list mapping out IDs nested inside this specific component layer.")


class BlokImplementationInputModel(BaseModel):
    "Base model for a Blok implementation manifest, which compiles all necessary information to materialize a Blok instance in the Arkitekt ecosystem."

    key: str = Field(description="The key of this Blok implementation.")
    dependencies: list[AgentDependencyInputModel] = Field(default_factory=list, description="The dependencies required by this Blok.")
    components: list[ComponentNodeInputModel] = Field(description="The UI component tree blueprint for this Blok.")
    catalog: Optional[str] = Field(default=None, description="The optional catalog name if this Blok should be registered inside a specific namespace in your Electron app's UI component registry.")
    description: Optional[str] = Field(default=None, description="A human-readable description about this Blok's purpose and functionality.")
    demo_state: Optional[dict] = Field(default=None, description="An optional JSON-serializable object providing demo state values for this Blok's internal reactive data model, useful for testing and development purposes.")


AssignWidgetInputModel.model_rebuild()
