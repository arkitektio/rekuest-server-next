"""Pydantic-backed demand types (action/state demands) and dynamic values."""

from __future__ import annotations

from typing import Optional

import strawberry
from pydantic import BaseModel
from rekuest_core import scalars as rscalars
from rekuest_core.objects import models as rmodels
from rekuest_core.objects import types as rtypes
from strawberry.experimental import pydantic


class ActionDemandModel(BaseModel):
    key: str
    hash: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    arg_matches: Optional[list[rmodels.PortMatchModel]] = None
    return_matches: Optional[list[rmodels.PortMatchModel]] = None
    protocols: Optional[list[str]] = None
    force_arg_length: Optional[int] = None
    force_return_length: Optional[int] = None


@pydantic.type(ActionDemandModel, description="Input model for action demand.")
class ActionDemand:
    key: str = strawberry.field(
        description="The key of the action demand. This is used to identify the action in the system.",
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
    arg_matches: list[rtypes.PortMatch] | None = strawberry.field(
        default=None,
        description="The demands for the action args and returns. This is used to identify the demand in the system.",
    )
    return_matches: list[rtypes.PortMatch] | None = strawberry.field(
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


class StateDemandModel(BaseModel):
    key: str
    hash: Optional[str] = None
    matches: Optional[list[rmodels.PortMatchModel]] = None
    protocols: Optional[list[str]] = None


@pydantic.type(StateDemandModel, description="The input for creating a action demand.")
class StateDemand:
    key: str = strawberry.field(
        description="The key of the action demand. This is used to identify the action in the system.",
    )
    hash: rscalars.ActionHash | None = strawberry.field(
        default=None,
        description="The hash of the state.",
    )
    matches: list[rtypes.PortMatch] | None = strawberry.field(
        default=None,
        description="The demands for the action args and returns. This is used to identify the demand in the system.",
    )
    protocols: list[strawberry.ID] | None = strawberry.field(
        default=None,
        description="The protocols that the action has to implement. This is used to identify the demand in the system.",
    )


class DynamicValueModel(BaseModel):
    """Base model for a dynamic value input, which can reference a variable in a Blok state instance.

    Attributes:
        literal: An optional static fallback literal value, passed as a serialized string or JSON primitive.
    """

    literal: str | None = None
    path: str | None = None
