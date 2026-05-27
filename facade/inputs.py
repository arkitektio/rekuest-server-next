from typing import Annotated, Any, Dict, List, Literal, Optional

import strawberry
from facade import enums, scalars
from pydantic import BaseModel, Field
from rekuest_core import enums as renums
from rekuest_core import scalars as rscalars

from rekuest_core.inputs import models as rimodels
from rekuest_core.inputs import types as ritypes
from strawberry import LazyType
from strawberry.experimental import pydantic
import uuid
from datalayer import scalars as dscalars  # noqa: F401


class MappedActionInputModel(BaseModel):
    key: str
    implementation: str
    dependencies: list["ResolvedDependencyInputModel"] | None = None


class MappedAgentInputModel(BaseModel):
    key: str
    agent: str
    mapped_actions: list[str]


class ResolvedDependencyInputModel(BaseModel):
    key: str
    mapped_agents: list[MappedAgentInputModel]
    auto_resolve: bool = False


@pydantic.input(
    MappedActionInputModel,
    description="The input for mapping an action to an implementation in a agent.",
)
class MappedActionInput:
    key: str = strawberry.field(description="The key of the action to map. This is used to identify the action in the system.")
    implementation: strawberry.ID = strawberry.field(description="The implementation ID to map the action to. This is used to identify the implementation in the system.")
    dependencies: list[Annotated["ResolvedDependencyInput", strawberry.lazy(__name__)]] | None = strawberry.field(
        default=None,
        description="The dependencies of the mapped action. This is used to identify the dependencies in the system.",
    )


@pydantic.input(
    MappedAgentInputModel,
    description="The input for mapping actions to implementations in a agent.",
)
class MappedAgentInput:
    key: str = strawberry.field(description="The key of the agent to map. This is used to identify the agent in the system.")
    agent: strawberry.ID = strawberry.field(description="The agent ID to map the actions to. This is used to identify the agent in the system.")
    mapped_actions: list[MappedActionInput] = strawberry.field(description="The list of action keys to map to implementations in the agent. This is used to identify the actions in the system.")


@pydantic.input(
    ResolvedDependencyInputModel,
    description="The input for mapping dependencies to implementations in a agent.",
)
class ResolvedDependencyInput:
    key: str = strawberry.field(description="The key of the dependency to map. This is used to identify the dependency in the system.")
    mapped_agents: list[MappedAgentInput] = strawberry.field(description="The list of mapped agents to map to implementations in agents. This is used to identify the mapped agents in the system.")
    auto_resolve: bool = strawberry.field(
        default=False,
        description="Whether this dependency should be automatically resolved by the system. If true, the system will attempt to find a agent that can resolve this dependency and assign it to the action when the action is assigned. This is used to enable automatic resolution of dependencies without requiring the user to specify a specific agent for the dependency.",
    )


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


@strawberry.input
class AutoResolveInput:
    action: strawberry.ID


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


@strawberry.input(description="Input for reserving an action. This is used to reserve an action for a waiter instance, optionally specifying the action or implementation to reserve, along with additional metadata for the reservation.")
class CreateDashboardInput:
    name: str = strawberry.field(description="The name of the dashboard.")
    bloks: list[str] = strawberry.field(default_factory=list, description="The list of blok IDs to include in the dashboard.")
    organization: str | None = strawberry.field(default=None, description="The organization ID to associate with the dashboard.")


@strawberry.input(description="Input for deleting a dashboard. This is used to delete a dashboard by its ID.")
class DeleteDashboardInput:
    id: strawberry.ID = strawberry.field(description="The ID of the dashboard to delete.")


@strawberry.input(description="Input for updating a dashboard. This is used to update the properties of a dashboard, such as its name, associated bloks, or organization.")
class DeleteMaterializedBlokInput:
    id: strawberry.ID = strawberry.field(description="The ID of the materialized blok to delete.")


@strawberry.input(description="Input for updating a materialized blok. This is used to update the properties of a materialized blok, such as its associated agent mappings.")
class UpdateMaterializedBlokInput:
    id: strawberry.ID = strawberry.field(description="The ID of the materialized blok to update.")
    agent_mappings: list[MappedAgentInput] | None = strawberry.field(
        default=None,
        description="The list of mapped agents to update the materialized blok with. This is used to update the agent mappings of the materialized blok.",
    )


@strawberry.input(description="Input for updating a dashboard. This is used to update the properties of a dashboard, such as its name, associated bloks, or organization.")
class UpdateDashboardInput:
    id: strawberry.ID = strawberry.field(description="The ID of the dashboard to update.")
    name: str | None = strawberry.field(default=None, description="The new name of the dashboard.")
    bloks: list[str] | None = strawberry.field(default=None, description="The new list of blok IDs to include in the dashboard. This will replace the existing list if provided.")
    organization: str | None = strawberry.field(default=None, description="The new organization ID to associate with the dashboard.")


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
    cached: bool | None = None
    log: bool | None = None
    capture: bool | None = None
    ephemeral: bool | None = None
    dependencies: list[ResolvedDependencyInputModel] | None = None
    is_hook: bool | None = None
    step: bool | None = None


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
    dependencies: list[ResolvedDependencyInput] | None = strawberry.field(
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


class CreateBlokInputModel(BaseModel):
    """Base model for creating a Blok, which is a reusable UI component with optional agent interactions.

    Attributes:
        name: The name of the Blok, used for identification in the system.
        dependencies: An optional list of agent dependencies declared in the Blok manifest, used to identify the Blok in the system.
        description: An optional description of the Blok and its purpose.
        catalog: An optional universal ID for the Blok.
        uri: The URI of the Blok, used to link to it in the system.
        components: An optional list of component nodes defining the Blok's visual structure and behavior.
    """

    name: str
    dependencies: list[rimodels.AgentDependencyInputModel] | None = None
    description: str | None = None
    catalog: str | None = None
    uri: str
    components: list[rimodels.ComponentNodeInputModel] | None = None
    demo_state: dict[str, Any] | None = None


@pydantic.input(CreateBlokInputModel, description="The input for creating a blok.")
class CreateBlokInput:
    name: str
    dependencies: list[ritypes.AgentDependencyInput] | None = strawberry.field(
        default=None,
        description="The dependencies of the blok. This is used to identify the blok in the system.",
    )
    description: str | None = strawberry.field(
        default=None,
        description="The description of the blok. This can described the blok and its purpose.",
    )
    catalog: str | None = strawberry.field(
        default=None,
        description="The universal id",
    )
    uri: str | None = strawberry.field(
        default=None,
        description="The URI of the blok. This can be used to link to the blok in the system.",
    )
    components: list[ritypes.ComponentNodeInput] | None = strawberry.field(
        default=None,
        description="The schema of the blok. This can be used to validate the blok input and output.",
    )
    demo_state: scalars.Args | None = strawberry.field(
        default=None,
        description="The initial state of the blok. This is used to set the initial state of the blok when it is materialized.",
    )


@strawberry.input(description="The input for updating a blok.")
class UpdateBlokInput:
    id: strawberry.ID
    name: str | None = strawberry.field(
        default=None,
        description="The name of the blok, used for identification in the system.",
    )
    description: str | None = strawberry.field(
        default=None,
        description="The description of the blok and its purpose.",
    )
    components: list[ritypes.ComponentNodeInput] | None = strawberry.field(
        default=None,
        description="The components of the blok. This is used to update the blok in the system.",
    )


@strawberry.input(description="The input for updating a blok.")
class DeleteBlokInput:
    id: strawberry.ID = strawberry.field(description="The blok ID to delete. This is used to identify the blok in the system.")


@strawberry.input(description="The input for updating a blok.")
class BlokAgentMappingInput:
    agent: strawberry.ID
    key: str


@strawberry.input(description="The input for creating a blok.")
class MaterializeBlokInput:
    blok: strawberry.ID
    dashboard: strawberry.ID | None = strawberry.field(
        default=None,
        description="The dashboard ID to materialize the blok in. If not provided, the blok will be materialized in the default dashboard.",
    )
    agent_mappings: list[BlokAgentMappingInput] | None = strawberry.field(
        default=None,
        description="The agent mappings for the blok. This is used to map the blok dependencies to agents in the system.",
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


class CreateThreeDModelInputModel(BaseModel):
    name: str
    description: str | None = None
    media: str
    transfer_function: str | None = None
    dependency: rimodels.AgentDependencyInputModel | None = None


@pydantic.input(CreateThreeDModelInputModel, description="The input for creating a 3D model.")
class CreateThreeDModelInput:
    name: str = strawberry.field(description="The name of the 3D model.")
    description: str | None = strawberry.field(default=None, description="A description of the 3D model.")
    media: dscalars.MediaLike = strawberry.field(description="The media store file for the 3D model.")
    transfer_function: str | None = strawberry.field(default=None, description="The function used to transfer the state of the model to properties of the scene. If not provided, a default function will be used.")
    dependency: ritypes.AgentDependencyInput | None = strawberry.field(default=None, description="The dependency to run the transfer function in. If not provided, the transfer function will be run in the default agent.")


class UpdateThreeDModelInputModel(BaseModel):
    id: str
    name: str | None = None
    description: str | None = None
    media: str | None = None


@pydantic.input(UpdateThreeDModelInputModel, description="The input for updating a 3D model.")
class UpdateThreeDModelInput:
    id: strawberry.ID = strawberry.field(description="The ID of the 3D model to update.")
    name: str | None = strawberry.field(default=None, description="The new name of the 3D model.")
    description: str | None = strawberry.field(default=None, description="The new description of the 3D model.")
    media: strawberry.ID | None = strawberry.field(default=None, description="The new media store file ID for the 3D model.")


class PlacementInputModel(BaseModel):
    role: str | None = None
    affine_matrix: list[list[float]] | None = None
    model: str | None = None
    agent: str | None = None


class DeleteThreeDModelInputModel(BaseModel):
    id: str


@pydantic.input(PlacementInputModel, description="The input for creating or updating a placement.")
class PlacementInput:
    role: str | None = strawberry.field(default=None, description="The role of the placement. This is used to identify the placement in the system.")
    affine_matrix: list[list[float]] | None = strawberry.field(default=None, description="The affine matrix for the placement. This is used to identify the placement in the system.")
    model: strawberry.ID | None = strawberry.field(default=None, description="The 3D model ID for the placement. This is used to identify the 3D model in the system.")
    agent: strawberry.ID | None = strawberry.field(default=None, description="The agent ID for the placement. This is used to identify the agent in the system.")
    blok: strawberry.ID | None = strawberry.field(default=None, description="A specific blok that should be used to visualize the state of the placement")


@pydantic.input(DeleteThreeDModelInputModel, description="The input for deleting a 3D model.")
class DeleteThreeDModelInput:
    id: strawberry.ID = strawberry.field(description="The ID of the 3D model to delete.")


class CreateSpaceInputModel(BaseModel):
    """Base model for creating a resolution.

    Attributes:
        name: Name of the resolution
        action_demands: List of action demands for the resolution
        state_demands: List of state demands for the resolution
        description: Description of the resolution
        url: URL associated with the resolution
    """

    name: str
    placements: list[PlacementInputModel] | None = None


@pydantic.input(
    CreateSpaceInputModel,
    description="The input for creating a space.",
)
class CreateSpaceInput:
    name: str = strawberry.field(description="The name of the space. This is used to identify the space in the system.")
    placements: list[PlacementInput] | None = strawberry.field(default=None, description="The placements to create in the space. This is used to identify the placements in the system.")


class CreateSpaceMembershipInputModel(BaseModel):
    """Base model for creating a resolution.

    Attributes:
        name: Name of the resolution
        action_demands: List of action demands for the resolution
        state_demands: List of state demands for the resolution
        description: Description of the resolution
        url: URL associated with the resolution
    """

    space_id: str
    agent_id: str


@pydantic.input(
    CreateSpaceMembershipInputModel,
    description="The input for creating a space membership.",
)
class CreateSpaceMembershipInput:
    space_id: str = strawberry.field(description="The ID of the space.")
    agent_id: str = strawberry.field(description="The ID of the agent.")


class UpdateSpaceInputModel(BaseModel):
    id: str
    name: str | None = None
    description: str | None = None


@pydantic.input(UpdateSpaceInputModel, description="The input for updating a space.")
class UpdateSpaceInput:
    id: strawberry.ID = strawberry.field(description="The ID of the space to update.")
    name: str | None = strawberry.field(default=None, description="The new name of the space.")
    description: str | None = strawberry.field(default=None, description="The new description of the space.")


class DeleteSpaceInputModel(BaseModel):
    id: str


@pydantic.input(DeleteSpaceInputModel, description="The input for deleting a space.")
class DeleteSpaceInput:
    id: strawberry.ID = strawberry.field(description="The ID of the space to delete.")


class CreatePlacementInputModel(PlacementInputModel):
    space: str
    pass


class UpdatePlacementInputModel(PlacementInputModel):
    id: str


@pydantic.input(CreatePlacementInputModel, description="The input for creating a placement.")
class CreatePlacementInput:
    space: str = strawberry.field(description="The ID of the space to create the placement in.")
    role: str | None = strawberry.field(default=None, description="The role for the placement.")
    affine_matrix: list[list[float]] | None = strawberry.field(default=None, description="The affine matrix for the placement.")
    model: strawberry.ID | None = strawberry.field(default=None, description="The model for the placement.")
    agent: strawberry.ID | None = strawberry.field(default=None, description="The agent ID to create the placement for. If not provided, the placement will be created for the default agent.")


@pydantic.input(UpdatePlacementInputModel, description="The input for updating a placement.")
class UpdatePlacementInput:
    id: strawberry.ID = strawberry.field(description="The ID of the placement to update.")
    role: str | None = strawberry.field(default=None, description="The new role for the placement.")
    affine_matrix: list[list[float]] | None = strawberry.field(default=None, description="The new affine matrix for the placement.")
    model: strawberry.ID | None = strawberry.field(default=None, description="The new model for the placement.")
    agent: strawberry.ID | None = strawberry.field(default=None, description="The new agent ID for the placement.")


class DeletePlacementInputModel(BaseModel):
    id: str


@pydantic.input(DeletePlacementInputModel, description="The input for deleting a placement.")
class DeletePlacementInput:
    id: strawberry.ID = strawberry.field(description="The ID of the placement to delete.")
