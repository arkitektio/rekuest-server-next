"""Inputs for assignations and the postman lifecycle controls."""

from typing import Any

import strawberry
from pydantic import BaseModel, Field
from rekuest_core import scalars as rscalars
from strawberry.experimental import pydantic

from facade import enums, scalars
from facade.inputs.dependency import ResolvedDependencyInput, ResolvedDependencyInputModel


class HookInputModel(BaseModel):
    """Base model for hook input data.

    Attributes:
        kind: The type/kind of hook to be executed
        hash: Hash identifier for the hook action
    """

    kind: enums.HookKind = Field(description="The kind of the hook. This is used to identify the hook in the system.")
    hash: str = Field(description="The hash of the hook. This is used to identify the hook in the system.")


@pydantic.input(
    HookInputModel,
    description="A hook is a function that is called when a action has reached a specific lifecycle point. Hooks are jsut actions that take an assignation as input and return a value.",
)
class HookInput:
    kind: enums.HookKind
    hash: rscalars.ActionHash


class AssignInputModel(BaseModel):
    """Base model for assigning arguments to an action.

    Attributes:
        action: Optional action ID to assign to
        implementation: Optional implementation ID for direct assignment
        agent: Optional agent ID for direct assignment
        action_hash: Optional hash of the action for identification
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

    action: str | None = Field(default=None, description="The action ID to assign to")
    dependency: str | None = Field(default=None, description="The dependency key.method to assign when running inside a resolved assignation")
    resolution: str | None = Field(
        default=None,
        description="The resolution ID to assign to when assining to a implementation with dependencies",
    )  # if assining to a implementation with dependencies
    implementation: str | None = Field(
        default=None,
        description="The implementation ID to assign to when directly assingint to a implementation",
    )
    agent: str | None = Field(
        default=None,
        description="The agent ID to assign to when directly assingint to a implementation",
    )
    action_hash: str | None = Field(
        default=None,
        description="The hash of the action. This is used to identify the action in the system.",
    )
    method: str | None = Field(default=None, description="The method key to assign when running inside a resolved assignation")
    interface: str | None = Field(
        default=None,
        description="The interface of the implementation. Only ussable if you also set agent",
    )
    hooks: list[HookInputModel] | None = Field(
        default=None,
        description="The hooks of the assignation. This is used to identify the assignation in the system.",
    )
    args: dict[str, Any] = Field(description="The args of the assignation. Its a dictionary of ports and values")
    reference: str | None = Field(
        default=None,
        description="The reference of the assignation. This is used to identify the assignation in the system.",
    )
    parent: str | None = Field(
        default=None,
        description="The parent ID of the assignation. This is used to identify the assignation in the system.",
    )
    cached: bool | None = Field(default=None, description="Whether the assignation should be cached")
    log: bool | None = Field(default=None, description="Whether the assignation should be logged")
    capture: bool | None = Field(default=None, description="Whether to capture the assignation.")
    ephemeral: bool | None = Field(default=None, description="Whether the assignation is ephemeral")
    dependencies: list[ResolvedDependencyInputModel] | None = Field(
        default=None,
        description="The dependencies of the assignation. This maps dependency keys to implementation IDs.",
    )
    is_hook: bool | None = Field(default=None, description="Whether the assignation is a hook")
    step: bool | None = Field(default=None, description="Whether the assignation should step. Ie. go to the next breakpoint")
    policy: enums.AssignPolicy | None = Field(default=None, description="The policy for the assignation. This defines how the assignation should be handled.")


@pydantic.input(AssignInputModel, description="The input for assigning args to a action.")
class AssignInput:
    action: strawberry.ID | None = None
    implementation: strawberry.ID | None = None
    agent: strawberry.ID | None = None
    action_hash: rscalars.ActionHash | None = None
    dependency: str | None = None
    method: str | None = None
    interface: str | None = None
    resolution: strawberry.ID | None = None
    hooks: list[HookInput] | None = strawberry.field(default_factory=list)
    capture: bool = False
    args: scalars.Args
    reference: str | None = None
    parent: strawberry.ID | None = None
    step: bool | None = False
    dependencies: list[ResolvedDependencyInput] | None = None
    policy: enums.AssignPolicy | None = None
    cached: bool = False
    ephemeral: bool = False
    log: bool = False
    is_hook: bool | None = False


class CancelInputModel(BaseModel):
    """Base model for canceling an assignation.

    Attributes:
        assignation: ID of the assignation to cancel
    """

    assignation: str = Field(description="The assignation ID to cancel")


@pydantic.input(CancelInputModel, description="The input for canceling an assignation.")
class CancelInput:
    assignation: strawberry.ID


class PauseInputModel(BaseModel):
    """Base model for pausing an assignation.

    Attributes:
        assignation: ID of the assignation to pause
    """

    assignation: str = Field(description="The assignation ID to pause")


@pydantic.input(PauseInputModel, description="The input for pausing an assignation.")
class PauseInput:
    assignation: strawberry.ID


class CollectInputModel(BaseModel):
    """Base model for collecting shelved items from drawers.

    Attributes:
        drawers: List of drawer IDs to collect from
    """

    drawers: list[str] = Field(description="The drawer ID to collect")


@pydantic.input(
    CollectInputModel,
    description="The input for collecting a shelved item in a drawer.",
)
class CollectInput:
    drawers: list[strawberry.ID]


class ResumeInputModel(BaseModel):
    """Base model for resuming a paused assignation.

    Attributes:
        assignation: ID of the assignation to resume
        step: resume only to the next breakpoint (the equivalent of the old step instruction)
    """

    assignation: str = Field(description="The assignation ID to resume")
    step: bool = Field(default=False, description="Resume only until the next breakpoint instead of running on freely.")


@pydantic.input(ResumeInputModel, description="The input for resuming an assignation.")
class ResumeInput:
    assignation: strawberry.ID
    step: bool = False


class InterruptInputModel(BaseModel):
    """Base model for interrupting an assignation.

    Attributes:
        assignation: ID of the assignation to interrupt
    """

    assignation: str = Field(description="The assignation ID to interrupt")


@pydantic.input(InterruptInputModel, description="The input for interrupting an assignation.")
class InterruptInput:
    assignation: strawberry.ID
