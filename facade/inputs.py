from typing import Any, Dict, Literal, Optional

import strawberry
from facade import enums, scalars
from pydantic import BaseModel, Field
from rekuest_core import enums as renums
from rekuest_core import scalars as rscalars

from rekuest_core.inputs import models as rimodels
from rekuest_core.inputs import types as ritypes
from rekuest_ui_core.inputs import models as uimodels
from rekuest_ui_core.inputs import types as uitypes
from strawberry import LazyType
from strawberry.experimental import pydantic
import uuid


class PinInputModel(BaseModel):
    id: str
    pin: bool


@pydantic.input(PinInputModel, description="The input for pinning an model.")
class PinInput:
    id: strawberry.ID
    pin: bool


class ReserveInputModel(BaseModel):
    reference: str = Field(default_factory=lambda: str(uuid.uuid4()))
    instance_id: str = Field(default="default")
    action: str | None = None
    implementation: str | None = None
    title: str | None = None
    hash: str | None = None
    binds: rimodels.BindsInputModel | None = None
    assignation_id: str | None = None


@pydantic.input(ReserveInputModel, description="The input for reserving a action.")
class ReserveInput:
    instance_id: scalars.InstanceID = strawberry.field(description="The instance ID of the waiter")
    action: strawberry.ID | None = strawberry.field(default=None, description="The action ID to reserve")
    implementation: strawberry.ID | None = strawberry.field(
        default=None,
        description="The implementation ID to reserve when directly reserving a implementation",
    )
    title: str | None = strawberry.field(
        default=None,
        description="The title of the reservation. This is used to identify the reservation in the system.",
    )
    hash: rscalars.ActionHash | None = strawberry.field(
        default=None,
        description="The hash of the reservation. This is used to identify the reservation in the system.",
    )
    reference: str | None = strawberry.field(
        default=None,
        description="The reference of the reservation. This is used to identify the reservation in the system.",
    )
    binds: ritypes.BindsInput | None = strawberry.field(
        default=None,
        description="The binds of the reservation. This is used to identify the reservation in the system.",
    )
    assignation_id: strawberry.ID | None = strawberry.field(
        default=None,
        description="The assignation ID of the reservation. This is used to identify the reservation in the system.",
    )


class HookInputModel(BaseModel):
    kind: enums.HookKind
    hash: str


class AssignInputModel(BaseModel):
    instance_id: str
    action: str | None = None
    implementation: str | None = None
    agent: str | None = None
    action_hash: str | None = None
    reservation: str | None = None
    interface: str | None = None
    hooks: list[HookInputModel] | None = None
    args: dict[str, Any]
    reference: str = Field(default_factory=lambda: str(uuid.uuid4()))
    parent: str | None = None
    cached: bool = False
    log: bool = False
    ephemeral: bool = False
    is_hook: bool = False
    step: bool = False


class CancelInputModel(BaseModel):
    assignation: str


@pydantic.input(CancelInputModel, description="The input for canceling an assignation.")
class CancelInput:
    assignation: strawberry.ID = strawberry.field(description="The assignation ID to cancel")


class PauseInputModel(BaseModel):
    assignation: str


@pydantic.input(PauseInputModel, description="The input for pausing an assignation.")
class PauseInput:
    assignation: strawberry.ID = strawberry.field(description="The assignation ID to pause")


class CollectInputModel(BaseModel):
    drawers: list[str]


@pydantic.input(
    CollectInputModel,
    description="The input for collecting a shelved item in a drawer.",
)
class CollectInput:
    drawers: list[strawberry.ID] = strawberry.field(description="The drawer ID to collect")


class ResumeInputModel(BaseModel):
    assignation: str


@pydantic.input(ResumeInputModel, description="The input for resuming an assignation.")
class ResumeInput:
    assignation: strawberry.ID = strawberry.field(description="The assignation ID to resume")


class StepInputModel(BaseModel):
    assignation: str


@pydantic.input(
    StepInputModel,
    description="The input for stepping an assignation. Stepping is used to go from one breakpoint to another.",
)
class StepInput:
    assignation: strawberry.ID = strawberry.field(description="The assignation ID to step")


class InterruptInputModel(BaseModel):
    assignation: str


@pydantic.input(InterruptInputModel, description="The input for interrupting an assignation.")
class InterruptInput:
    assignation: strawberry.ID = strawberry.field(description="The assignation ID to interrupt")


@pydantic.input(
    HookInputModel,
    description="A hook is a function that is called when a action has reached a specific lifecycle point. Hooks are jsut actions that take an assignation as input and return a value.",
)
class HookInput:
    kind: enums.HookKind = strawberry.field(description="The kind of the hook. This is used to identify the hook in the system.")
    hash: rscalars.ActionHash = strawberry.field(description="The hash of the hook. This is used to identify the hook in the system.")


@pydantic.input(AssignInputModel, description="The input for assigning args to a action.")
class AssignInput:
    instance_id: scalars.InstanceID = strawberry.field(default="default", description="The instance ID of the waiter")
    action: strawberry.ID | None = strawberry.field(default=None, description="The action ID to assign to")
    implementation: strawberry.ID | None = strawberry.field(
        default=None,
        description="The implementation ID to assign to when directly assingint to a implementation",
    )
    agent: strawberry.ID | None = strawberry.field(
        default=None,
        description="The agent ID to assign to when directly assingint to a implementation",
    )
    action_hash: rscalars.ActionHash | None = strawberry.field(
        default=None,
        description="The hash of the action. This is used to identify the action in the system.",
    )
    interface: str | None = strawberry.field(
        default=None,
        description="The interface of the implementation. Only ussable if you also set agent",
    )
    hooks: list[HookInput] | None = strawberry.field(
        default_factory=list,
        description="The hooks of the assignation. This is used to identify the assignation in the system.",
    )
    reservation: strawberry.ID | None = strawberry.field(
        default=None,
        description="The reservation ID to assign to. This is used to identify the reservation in the system.",
    )
    args: scalars.Args = strawberry.field(
        description="The args of the assignation. Its a dictionary of ports and values",
    )
    reference: str | None = strawberry.field(
        default=None,
        description="The reference of the assignation. This is used to identify the assignation in the system.",
    )
    parent: strawberry.ID | None = strawberry.field(
        default=None,
        description="The parent ID of the assignation. This is used to identify the assignation in the system.",
    )
    step: bool | None = strawberry.field(
        default=False,
        description="Whether the assignation should step. Ie. go to the next breakpoint",
    )
    cached: bool = False
    ephemeral: bool = False
    log: bool = False
    is_hook: bool | None = strawberry.field(default=False, description="Whether the assignation is a hook")




class PortMatchInputModel(BaseModel):
    at: int | None = None
    key: str | None = None
    kind: renums.PortKind | None = None
    identifier: str | None = None
    nullable: bool | None = None
    children: list["PortMatchInputModel"] | None = None


class ActionDemandInputModel(BaseModel):
    key: str | None = None
    hash: str | None = None
    name: str | None = None
    description: str | None = None
    arg_matches: list[PortMatchInputModel] | None = None
    return_matches: list[PortMatchInputModel] | None = None
    protocols: list[str] | None = None
    force_arg_length: int | None = None
    force_return_length: int | None = None


class SchemaDemandInputModel(BaseModel):
    key: str | None = None
    hash: str | None = None
    matches: list[PortMatchInputModel] | None = None
    protocols: list[str] | None = None



@strawberry.input(description="The input for creating a port match.")
class PortMatchInput:
    at: int | None = strawberry.field(
        default=None,
        description="The index of the port to match. ",
    )
    key: str | None = strawberry.field(
        default=None,
        description="The key of the port to match.",
    )
    kind: renums.PortKind | None = strawberry.field(
        default=None,
        description="The kind of the port to match. ",
    )
    identifier: str | None = strawberry.field(
        default=None,
        description="The identifier of the port to match. ",
    )
    nullable: bool | None = strawberry.field(
        default=None,
        description="Whether the port is nullable. ",
    )
    children: Optional[list[LazyType["PortMatchInput", __name__]]] = strawberry.field(
        default=None,
        description="The matches for the children of the port to match. ",
    )


@strawberry.input(description="The input for creating a port demand.")
class PortDemandInput:
    kind: enums.DemandKind = strawberry.field(
        description="The kind of the demand. You can ask for args or returns",
    )
    matches: list[PortMatchInput] | None = strawberry.field(
        default=None,
        description="The matches of the demand. ",
    )
    force_length: int | None = strawberry.field(
        default=None,
        description="Require that the action has a specific number of ports. This is used to identify the demand in the system.",
    )
    force_non_nullable_length: int | None = strawberry.field(
        default=None,
        description="Require that the action has a specific number of non-nullable ports. This is used to identify the demand in the system.",
    )
    force_structure_length: int | None = strawberry.field(
        default=None,
        description="Require that the action has a specific number of structure ports. This is used to identify the demand in the system.",
    )


@strawberry.input(description="The input for creating a action demand.")
class ActionDemandInput:
    key: str = strawberry.field(
        default=None,
        description="The key of the action. This is used to identify the action in the system.",
    )
    
    hash: rscalars.ActionHash | None = strawberry.field(
        default=None,
        description="The hash of the action. This is used to identify the action in the system.",
    )
    name: str | None = strawberry.field(
        default=None,
        description="The name of the action. This is used to identify the action in the system.",
    )
    description: str | None = strawberry.field(
        default=None,
        description="The description of the action. This can described the action and its purpose.",
    )
    arg_matches: list[PortMatchInput] | None = strawberry.field(
        default=None,
        description="The demands for the action args and returns. This is used to identify the demand in the system.",
    )
    return_matches: list[PortMatchInput] | None = strawberry.field(
        default=None,
        description="The demands for the action args and returns. This is used to identify the demand in the system.",
    )
    protocols: list[strawberry.ID] | None = strawberry.field(
        default=None,
        description="The protocols that the action has to implement. This is used to identify the demand in the system.",
    )
    force_arg_length: int | None = strawberry.field(
        default=None,
        description="Require that the action has a specific number of args. This is used to identify the demand in the system.",
    )
    force_return_length: int | None = strawberry.field(
        default=None,
        description="Require that the action has a specific number of returns. This is used to identify the demand in the system.",
    )


@strawberry.input(description="The input for creating a action demand.")
class SchemaDemandInput:
    key: str  = strawberry.field(
        default=None,
        description="The key of the action. This is used to identify the action in the system.",
    )
    hash: rscalars.ActionHash | None = strawberry.field(
        default=None,
        description="The hash of the state.",
    )
    matches: list[PortMatchInput] | None = strawberry.field(
        default=None,
        description="The demands for the action args and returns. This is used to identify the demand in the system.",
    )
    protocols: list[strawberry.ID] | None = strawberry.field(
        default=None,
        description="The protocols that the action has to implement. This is used to identify the demand in the system.",
    )


@strawberry.input(description="The input for creating an implementation demand.")
class ImplementationDemandInput:
    interface: str | None = strawberry.field(
        default=None,
        description="The interface that the implementation has to have",
    )
    action_demand: ActionDemandInput | None = strawberry.field(
        default=None,
        description="The action demand that the implementation has to have",
    )


@strawberry.input(description="The input for creating an implementation demand.")
class StateDemandInput:
    interface: str | None = strawberry.field(
        default=None,
        description="The interface that the implementation has to have",
    )
    schema_demand: SchemaDemandInput | None = strawberry.field(
        default=None,
        description="The action demand that the implementation has to have",
    )


class CreateImplementationInputModel(BaseModel):
    implementation: rimodels.ImplementationInputModel
    instance_id: str
    extension: str


class CreateForeignImplementationInputModel(BaseModel):
    implementation: rimodels.ImplementationInputModel
    instance_id: str
    extension: str


@pydantic.input(
    CreateImplementationInputModel,
    description="The input for creating a implementation.",
)
class CreateImplementationInput:
    implementation: ritypes.ImplementationInput = strawberry.field(description="The implementation to create. This is used to identify the implementation in the system.")
    instance_id: scalars.InstanceID = strawberry.field(description="The instance ID of the agent that this implementation belongs to.")
    extension: str = strawberry.field(description="The extension that manages this implementation")


@pydantic.input(
    CreateForeignImplementationInputModel,
    description="The input for creating a implementation in another agents extension.",
)
class CreateForeignImplementationInput:
    implementation: ritypes.ImplementationInput = strawberry.field(description="The implementation to create. This is used to identify the implementation in the system.")
    agent: strawberry.ID = strawberry.field(description="The agent ID to create the implementation in. This is used to identify the agent in the system.")
    extension: str = strawberry.field(description="The extension that manages this implementation")


class DeleteImplementationInputModel(BaseModel):
    implementation: str


@pydantic.input(
    DeleteImplementationInputModel,
    description="The input for deleting a implementation.",
)
class DeleteImplementationInput:
    implementation: strawberry.ID = strawberry.field(description="The implementation ID to delete. This is used to identify the implementation in the system.")


class SetExtensionImplementationsInputModel(BaseModel):
    implementation: rimodels.ImplementationInputModel
    instance_id: str
    extension: str
    run_cleanup: bool = False


@pydantic.input(
    SetExtensionImplementationsInputModel,
    description="The input for setting extension implementations.",
)
class SetExtensionImplementationsInput:
    implementations: list[ritypes.ImplementationInput] = strawberry.field(description="The implementations to set. This is used to identify the implementations in the system.")
    extension: str = strawberry.field(description="The extension that these implementations will be set to")
    run_cleanup: bool = strawberry.field(
        default=False,
        description="Whether to run the cleanup process after setting the implementations. If true, all implementations that are not in the list will be deleted.",
    )
    instance_id: scalars.InstanceID = strawberry.field(description="The instance ID of the agent that this extension belongs to.")


class CreateDashboardInputModel(BaseModel):
    tree: uimodels.UITreeInputModel | None = None


@pydantic.input(CreateDashboardInputModel, description="The input for creating a dashboard.")
class CreateDashboardInput:
    name: str | None = None
    tree: uitypes.UITreeInput | None = None
    panels: list[strawberry.ID] | None = None


@strawberry.input(description="The input for creating a blok.")
class CreateBlokInput:
    name: str
    action_demands: list[ActionDemandInput] | None = strawberry.field(
        default=None,
        description="The action demands of the blok. This is used to identify the blok in the system.",
    )
    state_demands: list[SchemaDemandInput] | None = strawberry.field(
        default=None,
        description="The state demands of the blok. This is used to identify the blok in the system.",
    )
    description: str | None = strawberry.field(
        default=None,
        description="The description of the blok. This can described the blok and its purpose.",
    )
    url: str = strawberry.field(
        default=None,
        description="The URL of the blok. This can be used to link to the blok in the system.",
    )

@strawberry.input(description="The input for creating a blok.")
class MaterializeBlokInput:
    blok: strawberry.ID 
    dashboard: strawberry.ID | None = strawberry.field(
        default=None,
        description="The dashboard ID to materialize the blok in. If not provided, the blok will be materialized in the default dashboard.",
    )
    agent: strawberry.ID | None = strawberry.field(
        default=None,
        description="The agent ID to materialize the blok in. If not provided, the blok will be materialized in the default agent"
    )
    


class CreateToolboxInputModel(BaseModel):
    name: str
    description: str


@pydantic.input(CreateToolboxInputModel, description="The input for creating a toolbox.")
class CreateToolboxInput:
    name: str = strawberry.field(description="The name of the toolbox. This is used to identify the toolbox in the system.")
    description: str | None = strawberry.field(
        default=None,
        description="The description of the toolbox. This can described the toolbox and its purpose.",
    )


class DeleteToolboxInputModel(BaseModel):
    id: str


@pydantic.input(DeleteToolboxInputModel, description="The input for deleting a toolbox.")
class DeleteToolboxInput:
    id: strawberry.ID = strawberry.field(description="The toolbox ID to delete. This is used to identify the toolbox in the system.")


class CreateShortcutInputModel(BaseModel):
    name: str
    description: str | None = None
    action: str
    implementation: str | None = None
    args: Dict[str, Any]
    allow_quick: bool = False
    use_returns: bool = False


@pydantic.input(CreateShortcutInputModel, description="The input for creating a shortcut.")
class CreateShortcutInput:
    action: strawberry.ID = strawberry.field(description="The action ID to create a shortcut for")
    name: str = strawberry.field(description="The name of the shortcut. This is used to identify the shortcut in the system.")
    toolbox: strawberry.ID | None = strawberry.field(
        default=None,
        description="The toolbox ID to create the shortcut in. If not provided, the shortcut will be created in the default toolbox.",
    )
    description: str | None = strawberry.field(
        default=None,
        description="The description of the shortcut.This can described the shortcut and its purpose.",
    )
    implementation: strawberry.ID | None = strawberry.field(
        default=None,
        description="The implementation ID to create the shortcut for. If not provided, the shortcut will be created for the action.",
    )
    args: scalars.Args = strawberry.field(description="The arguments to pre-pass to the shortcut. This is used to identify the shortcut in the system.")
    allow_quick: bool = strawberry.field(
        default=False,
        description="Whether to allow quick shortcuts. Quick shorts are shortcuts that can be autorun without scpeific assignment",
    )
    use_returns: bool = strawberry.field(
        default=False,
        description="Whether when running the short the returns should be used further. Allows to create mini pipelines",
    )


class DeleteShortcutInputModel(BaseModel):
    id: str


@pydantic.input(DeleteShortcutInputModel, description="The input for deleting a shortcut.")
class DeleteShortcutInput:
    id: strawberry.ID


class StateSchemaInputModel(BaseModel):
    ports: list[rimodels.PortInputModel]
    name: str


@pydantic.input(StateSchemaInputModel, description="The input for creating a state schema.")
class StateSchemaInput:
    ports: list[ritypes.PortInput] = strawberry.field(description="The ports of the state schema. This is used to identify the state schema in the system.")
    name: str = strawberry.field(description="The name of the state schema. This is used to identify the state schema in the system.")


class CreateStateSchemaInputModel(BaseModel):
    state_schema: StateSchemaInputModel
    instance_id: str


@pydantic.input(CreateStateSchemaInputModel, description="The input for creating a state schema.")
class CreateStateSchemaInput:
    state_schema: StateSchemaInput = strawberry.field(description="The state schema to create. This is used to identify the state schema in the system.")


class SetStateInputModel(BaseModel):
    interface: str
    instance_id: str
    value: Dict[str, Any]


@pydantic.input(SetStateInputModel, description="The input for setting a state schema.")
class SetStateInput:
    interface: str = strawberry.field(description="The state schema to set. This is used to identify the state schema in the system.")
    instance_id: scalars.InstanceID = strawberry.field(description="The instance ID of the agent that this state belongs to.")
    value: scalars.Args = strawberry.field(description="The value to set the state schema to. This is used to identify the state schema in the system.")


class StateInitInputModel(BaseModel):
    state_schema: strawberry.ID
    value: Dict[str, Any]


@pydantic.input(StateInitInputModel, description="The initializing input for a state schema.")
class StateInitInput:
    state_schema: strawberry.ID = strawberry.field(description="The state schema to initialize. This is used to identify the state schema in the system.")
    value: scalars.Args = strawberry.field(description="The value to set the state schema to. This is used to identify the state schema in the system.")


class StateImplementationInputModel(BaseModel):
    interface: str
    state_schema: StateSchemaInputModel = strawberry.field(description="The state schema to set. This is used to identify the state schema in the system.")
    initial: Dict[str, Any]


@pydantic.input(StateImplementationInputModel, description="The input for initializing a state schema.")
class StateImplementationInput:
    interface: str = strawberry.field(description="The interface of the implementation. Only ussable if you also set agent")
    state_schema: StateSchemaInput = strawberry.field(description="The state schema to set. This is used to identify the state schema in the system.")
    initial: scalars.Args = strawberry.field(description="The value to set the state schema to. This is used to identify the state schema in the system.")


class SetAgentStatesInputModel(BaseModel):
    implementations: list[StateImplementationInputModel]
    instance_id: str


@pydantic.input(
    SetAgentStatesInputModel,
    description="The input for setting a state schema to an agent.",
)
class SetAgentStatesInput:
    implementations: list[StateImplementationInput] = strawberry.field(description="The implementations of the state schemas. This is used to identify the state schemas in the system.")
    instance_id: scalars.InstanceID = strawberry.field(description="The instance ID of the agent that this state belongs to.")


class JSONPatchInputModel(BaseModel):
    op: Literal["add", "remove", "replace", "move", "copy", "test"]
    path: str
    value: Any | None = None


class UpdateStateInputModel(BaseModel):
    interface: str
    instance_id: str
    patches: list[JSONPatchInputModel]


@pydantic.input(UpdateStateInputModel, description="The input for updating a state schema.")
class UpdateStateInput:
    interface: str = strawberry.field(description="The state schema to update. This is used to identify the state schema in the system.")
    instance_id: scalars.InstanceID = strawberry.field(description="The instance ID of the agent that this state belongs to.")
    patches: list[scalars.Args]


class ArchiveStateInputModel(BaseModel):
    state_schema: strawberry.ID


@pydantic.input(ArchiveStateInputModel, description="The input for archiving a state schema.")
class ArchiveStateInput:
    state_schema: strawberry.ID = strawberry.field(description="The state schema to archive. This is used to identify the state schema in the system.")
