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


class ResolvedDependencyInputModel(BaseModel):
    """Base model for mapping dependencies to implementations.

    Attributes:
        key: The dependency key
        implementation: The implementation ID to map to the dependency
    """

    dependency: str
    resolution_key: str | None = None
    key: str
    implementation: str
    down_stream_resolution: str | None = None


class PatchInputModel(BaseModel):
    """Base model for JSON Patch operations.

    Attributes:
        op: The JSON Patch operation (add, remove, replace, move, copy, test)
    """

    op: str
    path: str
    value: Optional[Any]
    state_name: str
    current_rev: int
    future_rev: int
    session_id: str
    correlation_id: str | None = None
    global_current_rev: int
    global_future_rev: int


@pydantic.input(
    PatchInputModel,
    description="The input for updating a state using JSON Patch operations.",
)
class PatchInput:
    op: str = strawberry.field(description="The JSON Patch operation to perform. This can be add, remove, replace, move, copy, or test.")
    path: str = strawberry.field(description="The JSON Pointer path to the target value to apply the patch operation on.")
    value: rscalars.AnyDefault = strawberry.field(description="The value to be used in the patch operation. This is required for add, replace, and test operations, and should be null for remove, move, and copy operations.")
    state_name: str = strawberry.field(description="The name of the state to apply the patch to. This is used to identify the state in the system.")
    current_rev: int = strawberry.field(description="The current revision number of the state. This is used for optimistic concurrency control to ensure that the patch is applied to the correct version of the state.")
    future_rev: int = strawberry.field(description="The future revision number of the state after the patch is applied. This is used for optimistic concurrency control to ensure that the patch is applied to the correct version of the state.")
    session_id: str = strawberry.field(description="The session ID of the client applying the patch. This is used for tracking and auditing purposes.")
    correlation_id: str | None = strawberry.field(
        default=None,
        description="An optional correlation ID to associate with the patch operation. This can be used for tracking and debugging purposes across distributed systems.",
    )
    global_current_rev: int | None = strawberry.field(
        default=None,
        description="The global revision number of the state. This is used for conflict detection in distributed systems where multiple clients may be applying patches concurrently.",
    )
    global_future_rev: int | None = strawberry.field(
        default=None,
        description="The global future revision number of the state after the patch is applied. This is used for conflict detection in distributed systems where multiple clients may be applying patches concurrently.",
    )


class LogPatchesInputModel(BaseModel):
    """Base model for logging state events.

    Attributes:
        instance_id: The instance ID of the state
        interface: The interface of the state
        value: The value of the state event
    """

    instance_id: str
    patches: list[PatchInputModel]


@pydantic.input(
    LogPatchesInputModel,
    description="The input for logging state patches.",
)
class LogPatchesInput:
    instance_id: str = strawberry.field(description="The instance ID of the state. This is used to identify the state in the system.")
    patches: list[PatchInput] = strawberry.field(description="The list of patches applied to the state. This is used to log the changes made to the state.")


class LogSnapshotInputModel(BaseModel):
    """Base model for logging state snapshots.

    Attributes:
        instance_id: The instance ID of the state
        interface: The interface of the state
        value: The value of the state snapshot
    """

    instance_id: str
    interface: str
    value: Any


@pydantic.input(
    LogSnapshotInputModel,
    description="The input for logging state snapshots.",
)
class LogSnapshotInput:
    instance_id: str = strawberry.field(description="The instance ID of the state. This is used to identify the state in the system.")
    value: rscalars.AnyDefault = strawberry.field(description="The value of the state snapshot (index by state_keys). This is used to log the current state of the system.")


@pydantic.input(
    ResolvedDependencyInputModel,
    description="The input for mapping a dependency to an implementation.",
)
class ResolvedDependencyInput:
    dependency: strawberry.ID = strawberry.field(description="The dependency ID to map.")
    resolution_key: str | None = strawberry.field(
        default=None,
        description="An optional key to identify this resolution in the context of its parent resolution.",
    )
    key: str = strawberry.field(description="The key of the dependency to map.")
    implementation: strawberry.ID = strawberry.field(description="The implementation ID to map to the dependency.")
    down_stream_resolution: strawberry.ID | None = strawberry.field(
        default=None,
        description="The resolution ID for the down stream resolution of the dependency.",
    )


@strawberry.input
class AutoResolveInput:
    implementation: strawberry.ID


class CreateResolutionInputModel(BaseModel):
    """Base model for creating a resolution.

    Attributes:
        name: Name of the resolution
        action_demands: List of action demands for the resolution
        state_demands: List of state demands for the resolution
        description: Description of the resolution
        url: URL associated with the resolution
    """

    name: str
    resolved_dependencies: list[ResolvedDependencyInputModel] | None = None


class UpdateResolutionInputModel(BaseModel):
    """Base model for creating a resolution.

    Attributes:
        name: Name of the resolution
        action_demands: List of action demands for the resolution
        state_demands: List of state demands for the resolution
        description: Description of the resolution
        url: URL associated with the resolution
    """

    id: str
    name: str
    resolved_dependencies: list[ResolvedDependencyInputModel] | None = None


@pydantic.input(
    UpdateResolutionInputModel,
    description="The input for creating a resolution.",
)
class UpdateResolutionInput:
    id: strawberry.ID = strawberry.field(description="The ID of the resolution. This is used to identify the resolution in the system.")
    name: str = strawberry.field(description="The name of the resolution. This is used to identify the resolution in the system.")
    resolved_dependencies: list[ResolvedDependencyInput] | None = strawberry.field(
        default=None,
        description="The resolved dependencies of the resolution. All other fields will be replaced.",
    )


class CreateResolutionInputModel(BaseModel):
    """Base model for creating a resolution.

    Attributes:
        name: Name of the resolution
        action_demands: List of action demands for the resolution
        state_demands: List of state demands for the resolution
        description: Description of the resolution
        url: URL associated with the resolution
    """

    key: str
    name: str
    resolved_dependencies: list[ResolvedDependencyInputModel] | None = None


@pydantic.input(
    CreateResolutionInputModel,
    description="The input for creating a resolution.",
)
class CreateResolutionInput:
    key: str = strawberry.field(description="The key of the resolution. This is used to identify the resolution in the system.")
    implementation: strawberry.ID = strawberry.field(description="The implementation ID of the resolution. This is used to identify the resolution in the system.")
    name: str = strawberry.field(description="The name of the resolution. This is used to identify the resolution in the system.")
    resolved_dependencies: list[ResolvedDependencyInput] | None = strawberry.field(
        default=None,
        description="The resolved dependencies of the resolution. This is used to identify the resolution in the system.",
    )


class DeleteResolutionInputModel(BaseModel):
    """Base model for deleting a resolution.

    Attributes:
        id: The unique identifier of the resolution to delete
    """

    id: str


@pydantic.input(
    DeleteResolutionInputModel,
    description="The input for deleting a resolution.",
)
class DeleteResolutionInput:
    id: strawberry.ID = strawberry.field(description="The ID of the resolution to delete.")


class PinInputModel(BaseModel):
    """Base model for pinning input data.

    Attributes:
        id: The unique identifier of the item to pin
        pin: Boolean flag indicating whether to pin or unpin
    """

    id: str
    pin: bool


@pydantic.input(PinInputModel, description="The input for pinning an model.")
class PinInput:
    id: strawberry.ID
    pin: bool


class BounceInputModel(BaseModel):
    """Base model for bouncing an agent.

    Attributes:
        agent: ID of the agent to bounce
    """

    agent: str
    duration: int | None = None


@pydantic.input(BounceInputModel, description="The input for bouncing an agent.")
class BounceInput:
    agent: strawberry.ID = strawberry.field(description="The agent ID to bounce.")
    duration: int | None = strawberry.field(default=None, description="The duration to bounce the agent for.")


class KickInputModel(BaseModel):
    """Base model for bouncing an agent.

    Attributes:
        agent: ID of the agent to bounce
    """

    agent: str
    reason: str | None = None


@pydantic.input(KickInputModel, description="The input for bouncing an agent.")
class KickInput:
    agent: strawberry.ID = strawberry.field(description="The agent ID to bounce.")
    reason: str | None = strawberry.field(default=None, description="The reason for kicking the agent.")


class BlockInputModel(BaseModel):
    """Base model for bouncing an agent.

    Attributes:
        agent: ID of the agent to bounce
    """

    agent: str
    reason: str | None = None


@pydantic.input(BlockInputModel, description="The input for bouncing an agent.")
class BlockInput:
    agent: strawberry.ID = strawberry.field(description="The agent ID to bounce.")
    reason: str | None = strawberry.field(default=None, description="The reason for kicking the agent.")


class UnblockInputModel(BaseModel):
    """Base model for bouncing an agent.

    Attributes:
        agent: ID of the agent to bounce
    """

    agent: str
    reason: str | None = None


@pydantic.input(UnblockInputModel, description="The input for bouncing an agent.")
class UnblockInput:
    agent: strawberry.ID = strawberry.field(description="The agent ID to unblock.")
    reason: str | None = strawberry.field(default=None, description="The reason for unblocking the agent.")


class ReserveInputModel(BaseModel):
    """Base model for reserving an action.

    Attributes:
        reference: Unique reference identifier for the reservation
        instance_id: Instance identifier of the waiter (defaults to "default")
        action: Optional action ID to reserve
        implementation: Optional implementation ID for direct implementation reservation
        title: Optional title for the reservation
        hash: Optional hash for reservation identification
        binds: Optional binds configuration for the reservation
        assignation_id: Optional assignation ID associated with the reservation
    """

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
    instance_id: scalars.InstanceId = strawberry.field(description="The instance ID of the waiter")
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
    """Base model for hook input data.

    Attributes:
        kind: The type/kind of hook to be executed
        hash: Hash identifier for the hook action
    """

    kind: enums.HookKind
    hash: str


class AssignInputModel(BaseModel):
    """Base model for assigning arguments to an action.

    Attributes:
        instance_id: Instance identifier of the waiter
        action: Optional action ID to assign to
        implementation: Optional implementation ID for direct assignment
        agent: Optional agent ID for direct assignment
        action_hash: Optional hash of the action for identification
        reservation: Optional reservation ID to assign to
        interface: Optional interface of the implementation
        hooks: Optional list of hooks for the assignation
        args: Dictionary of arguments/ports and values
        reference: Unique reference identifier for the assignation
        parent: Optional parent ID of the assignation
        cached: Whether the assignation should be cached
        log: Whether the assignation should be logged
        ephemeral: Whether the assignation is ephemeral
        is_hook: Whether the assignation is a hook
        step: Whether the assignation should step to breakpoints
    """

    instance_id: str
    action: str | None = None
    dependency: str | None = None
    resolution: str | None = None  # if assining to a implementation with dependencies
    implementation: str | None = None
    agent: str | None = None
    action_hash: str | None = None
    method: str | None = None
    reservation: str | None = None
    interface: str | None = None
    hooks: list[HookInputModel] | None = None
    args: dict[str, Any]
    reference: str | None = None
    parent: str | None = None
    cached: bool = False
    log: bool = False
    capture: bool = False
    ephemeral: bool = False
    dependencies: dict[str, str] | None = None
    is_hook: bool = False
    step: bool = False


class CancelInputModel(BaseModel):
    """Base model for canceling an assignation.

    Attributes:
        assignation: ID of the assignation to cancel
    """

    assignation: str


@pydantic.input(CancelInputModel, description="The input for canceling an assignation.")
class CancelInput:
    assignation: strawberry.ID = strawberry.field(description="The assignation ID to cancel")


class PauseInputModel(BaseModel):
    """Base model for pausing an assignation.

    Attributes:
        assignation: ID of the assignation to pause
    """

    assignation: str


@pydantic.input(PauseInputModel, description="The input for pausing an assignation.")
class PauseInput:
    assignation: strawberry.ID = strawberry.field(description="The assignation ID to pause")


class CollectInputModel(BaseModel):
    """Base model for collecting shelved items from drawers.

    Attributes:
        drawers: List of drawer IDs to collect from
    """

    drawers: list[str]


@pydantic.input(
    CollectInputModel,
    description="The input for collecting a shelved item in a drawer.",
)
class CollectInput:
    drawers: list[strawberry.ID] = strawberry.field(description="The drawer ID to collect")


class ResumeInputModel(BaseModel):
    """Base model for resuming a paused assignation.

    Attributes:
        assignation: ID of the assignation to resume
    """

    assignation: str


@pydantic.input(ResumeInputModel, description="The input for resuming an assignation.")
class ResumeInput:
    assignation: strawberry.ID = strawberry.field(description="The assignation ID to resume")


class StepInputModel(BaseModel):
    """Base model for stepping an assignation through breakpoints.

    Attributes:
        assignation: ID of the assignation to step
    """

    assignation: str


@pydantic.input(
    StepInputModel,
    description="The input for stepping an assignation. Stepping is used to go from one breakpoint to another.",
)
class StepInput:
    assignation: strawberry.ID = strawberry.field(description="The assignation ID to step")


class InterruptInputModel(BaseModel):
    """Base model for interrupting an assignation.

    Attributes:
        assignation: ID of the assignation to interrupt
    """

    assignation: str


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
    instance_id: scalars.InstanceId = strawberry.field(default="default", description="The instance ID of the waiter")
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
    dependency: str | None = strawberry.field(default=None, description="The dependency key.method to assign when running inside a resolved assignation")
    method: str | None = strawberry.field(default=None, description="The method key to assign when running inside a resolved assignation")
    interface: str | None = strawberry.field(
        default=None,
        description="The interface of the implementation. Only ussable if you also set agent",
    )
    resolution: strawberry.ID | None = strawberry.field(
        default=None,
        description="The resolution ID to assign to when assining to a implementation with dependencies",
    )
    hooks: list[HookInput] | None = strawberry.field(
        default_factory=list,
        description="The hooks of the assignation. This is used to identify the assignation in the system.",
    )
    reservation: strawberry.ID | None = strawberry.field(
        default=None,
        description="The reservation ID to assign to. This is used to identify the reservation in the system.",
    )
    capture: bool = strawberry.field(
        default=False,
        description="Whether to capture the assignation.",
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
    dependencies: scalars.Args | None = strawberry.field(
        default=None,
        description="The dependencies of the assignation. This maps dependency keys to implementation IDs.",
    )
    policy: enums.AssignPolicy | None = strawberry.field(
        default=None,
        description="The policy for the assignation. This defines how the assignation should be handled.",
    )
    cached: bool = False
    ephemeral: bool = False
    log: bool = False
    is_hook: bool | None = strawberry.field(default=False, description="Whether the assignation is a hook")


class PortMatchInputModel(BaseModel):
    """Base model for matching ports in action/schema demands.

    Attributes:
        at: Optional index of the port to match
        key: Optional key of the port to match
        kind: Optional kind of the port to match
        identifier: Optional identifier of the port to match
        nullable: Optional flag indicating if the port is nullable
        children: Optional list of child port matches for nested structures
    """

    at: int | None = None
    key: str | None = None
    kind: renums.PortKind | None = None
    identifier: str | None = None
    nullable: bool | None = None
    children: list["PortMatchInputModel"] | None = None


class ActionDemandInputModel(BaseModel):
    """Base model for demanding specific actions with criteria.

    Attributes:
        key: Optional key of the action for identification
        hash: Optional hash of the action for identification
        name: Optional name of the action for identification
        description: Optional description of the action
        arg_matches: Optional list of argument port matches
        return_matches: Optional list of return port matches
        protocols: Optional list of protocols the action must implement
        force_arg_length: Optional required number of arguments
        force_return_length: Optional required number of returns
    """

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
    """Base model for demanding specific schemas with criteria.

    Attributes:
        key: Optional key of the schema for identification
        hash: Optional hash of the schema for identification
        matches: Optional list of port matches for the schema
        protocols: Optional list of protocols the schema must implement
    """

    key: str | None = None
    hash: str | None = None
    matches: list[PortMatchInputModel] | None = None
    protocols: list[str] | None = None


@strawberry.input(description="The input for creating a port demand.")
class PortDemandInput:
    kind: enums.DemandKind = strawberry.field(
        description="The kind of the demand. You can ask for args or returns",
    )
    matches: list[ritypes.PortMatchInput] | None = strawberry.field(
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
    arg_matches: list[ritypes.PortMatchInput] | None = strawberry.field(
        default=None,
        description="The demands for the action args and returns. This is used to identify the demand in the system.",
    )
    return_matches: list[ritypes.PortMatchInput] | None = strawberry.field(
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
    key: str = strawberry.field(
        default=None,
        description="The key of the action. This is used to identify the action in the system.",
    )
    hash: rscalars.ActionHash | None = strawberry.field(
        default=None,
        description="The hash of the state.",
    )
    matches: list[ritypes.PortMatchInput] | None = strawberry.field(
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
    """Base model for creating an implementation.

    Attributes:
        implementation: Implementation configuration data
        instance_id: Instance ID of the agent this implementation belongs to
        extension: Extension that manages this implementation
    """

    implementation: rimodels.ImplementationInputModel
    instance_id: str
    extension: str


class CreateForeignImplementationInputModel(BaseModel):
    """Base model for creating an implementation in another agent's extension.

    Attributes:
        implementation: Implementation configuration data
        instance_id: Instance ID of the agent to create implementation in
        extension: Extension that manages this implementation
    """

    implementation: rimodels.ImplementationInputModel
    instance_id: str
    extension: str


@pydantic.input(
    CreateImplementationInputModel,
    description="The input for creating a implementation.",
)
class CreateImplementationInput:
    implementation: ritypes.ImplementationInput = strawberry.field(description="The implementation to create. This is used to identify the implementation in the system.")
    instance_id: scalars.InstanceId = strawberry.field(description="The instance ID of the agent that this implementation belongs to.")
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
    """Base model for deleting an implementation.

    Attributes:
        implementation: ID of the implementation to delete
    """

    implementation: str


@pydantic.input(
    DeleteImplementationInputModel,
    description="The input for deleting a implementation.",
)
class DeleteImplementationInput:
    implementation: strawberry.ID = strawberry.field(description="The implementation ID to delete. This is used to identify the implementation in the system.")


class SetExtensionImplementationsInputModel(BaseModel):
    """Base model for setting extension implementations.

    Attributes:
        implementation: Implementation configuration data
        instance_id: Instance ID of the agent this extension belongs to
        extension: Extension identifier
        run_cleanup: Whether to run cleanup after setting implementations
    """

    implementation: rimodels.ImplementationInputModel
    instance_id: str
    extension: str
    run_cleanup: bool = False


@pydantic.input(
    SetExtensionImplementationsInputModel,
    description="The input for setting extension implementations.",
)
class SetExtensionImplementationsInput:
    locks: list[ritypes.LockSchemaInput] | None = strawberry.field(
        default=None,
        description="The locks to set on the implementations. This is used to identify the locks in the system.",
    )
    implementations: list[ritypes.ImplementationInput] = strawberry.field(description="The implementations to set. This is used to identify the implementations in the system.")
    extension: str = strawberry.field(description="The extension that these implementations will be set to")
    run_cleanup: bool = strawberry.field(
        default=False,
        description="Whether to run the cleanup process after setting the implementations. If true, all implementations that are not in the list will be deleted.",
    )
    instance_id: scalars.InstanceId = strawberry.field(description="The instance ID of the agent that this extension belongs to.")


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
    agent: strawberry.ID | None = strawberry.field(default=None, description="The agent ID to materialize the blok in. If not provided, the blok will be materialized in the default agent")


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
    bind_number: int | None = None


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
    bind_number: int | None = strawberry.field(
        default=None,
        description="The bind number of the shortcut. This is used to identify the shortcut in the system.",
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
    instance_id: scalars.InstanceId = strawberry.field(description="The instance ID of the agent that this state belongs to.")
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
    instance_id: scalars.InstanceId = strawberry.field(description="The instance ID of the agent that this state belongs to.")


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
    instance_id: scalars.InstanceId = strawberry.field(description="The instance ID of the agent that this state belongs to.")
    patches: list[scalars.Args]


class ArchiveStateInputModel(BaseModel):
    state_schema: strawberry.ID


@pydantic.input(ArchiveStateInputModel, description="The input for archiving a state schema.")
class ArchiveStateInput:
    state_schema: strawberry.ID = strawberry.field(description="The state schema to archive. This is used to identify the state schema in the system.")
