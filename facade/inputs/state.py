"""Inputs for state patches, snapshots and updates."""

from typing import Any, Optional

import strawberry
from pydantic import BaseModel
from rekuest_core import scalars as rscalars
from strawberry.experimental import pydantic


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
        interface: The interface of the state
        value: The value of the state event
    """

    patches: list[PatchInputModel]


@pydantic.input(
    LogPatchesInputModel,
    description="The input for logging state patches.",
)
class LogPatchesInput:
    patches: list[PatchInput] = strawberry.field(description="The list of patches applied to the state. This is used to log the changes made to the state.")


class LogSnapshotInputModel(BaseModel):
    """Base model for logging state snapshots.

    Attributes:
        interface: The interface of the state
        value: The value of the state snapshot
    """

    interface: str
    value: Any


@pydantic.input(
    LogSnapshotInputModel,
    description="The input for logging state snapshots.",
)
class LogSnapshotInput:
    value: rscalars.AnyDefault = strawberry.field(description="The value of the state snapshot (index by state_keys). This is used to log the current state of the system.")
