"""Inputs for reservations, assignations and the postman lifecycle controls."""

from typing import Any

import strawberry
import uuid
from pydantic import BaseModel, Field
from rekuest_core import scalars as rscalars
from rekuest_core.inputs import models as rimodels
from strawberry.experimental import pydantic

from facade import enums, scalars
from facade.inputs.dependency import ResolvedDependencyInput, ResolvedDependencyInputModel


class ReserveInputModel(BaseModel):
    """Base model for reserving an action.

    Attributes:
        reference: Unique reference identifier for the reservation
        action: Optional action ID to reserve
        implementation: Optional implementation ID for direct implementation reservation
        title: Optional title for the reservation
        hash: Optional hash for reservation identification
        binds: Optional binds configuration for the reservation
        assignation_id: Optional assignation ID associated with the reservation
    """

    reference: str = Field(default_factory=lambda: str(uuid.uuid4()))
    action: str | None = None
    implementation: str | None = None
    title: str | None = None
    hash: str | None = None
    binds: rimodels.BindsInputModel | None = None
    assignation_id: str | None = None


@pydantic.input(ReserveInputModel, description="The input for reserving a action.")
class ReserveInput:
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


@pydantic.input(
    HookInputModel,
    description="A hook is a function that is called when a action has reached a specific lifecycle point. Hooks are jsut actions that take an assignation as input and return a value.",
)
class HookInput:
    kind: enums.HookKind = strawberry.field(description="The kind of the hook. This is used to identify the hook in the system.")
    hash: rscalars.ActionHash = strawberry.field(description="The hash of the hook. This is used to identify the hook in the system.")


class AssignInputModel(BaseModel):
    """Base model for assigning arguments to an action.

    Attributes:
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


@pydantic.input(AssignInputModel, description="The input for assigning args to a action.")
class AssignInput:
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


@pydantic.input(InterruptInputModel, description="The input for interrupting an assignation.")
class InterruptInput:
    assignation: strawberry.ID = strawberry.field(description="The assignation ID to interrupt")
