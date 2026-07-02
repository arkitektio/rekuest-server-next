"""Pydantic-backed demand types (action/state demands) and dynamic values."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field
from rekuest_core import scalars as rscalars
from rekuest_core.objects import models as rmodels
from rekuest_core.objects import types as rtypes
from strawberry.experimental import pydantic


class ActionDemandModel(BaseModel):
    """Pure matching criteria for an action — mirrors ``ActionDemandInputModel``."""

    hash: Optional[str] = Field(default=None, description="The exact hash of the action. When set, matching short-circuits on the hash.")
    key: Optional[str] = Field(default=None, description="The action's key within its app, e.g. 'open_image'.")
    app: Optional[str] = Field(default=None, description="The identifier of the app providing the action, e.g. 'imagej'.")
    version: Optional[str] = Field(default=None, description="The exact version of the action.")
    name: Optional[str] = Field(default=None, description="The display name of the action to match.")
    arg_matches: Optional[list[rmodels.PortMatchModel]] = Field(default=None, description="The matches the action's arg ports must satisfy.")
    return_matches: Optional[list[rmodels.PortMatchModel]] = Field(default=None, description="The matches the action's return ports must satisfy.")
    protocols: Optional[list[str]] = Field(default=None, description="Protocols (by name) the action must implement.")
    force_arg_length: Optional[int] = Field(default=None, description="Require that the action has exactly this number of root args.")
    force_return_length: Optional[int] = Field(default=None, description="Require that the action has exactly this number of root returns.")
    pure: Optional[bool] = Field(default=None, description="Require the action to be (or not be) pure.")
    idempotent: Optional[bool] = Field(default=None, description="Require the action to be (or not be) idempotent.")
    stateful: Optional[bool] = Field(default=None, description="Require the action to be (or not be) stateful.")


@pydantic.type(ActionDemandModel, description="Pure matching criteria for an action (app/key preferred; matches loosen).")
class ActionDemand:
    hash: rscalars.ActionHash | None = None
    key: str | None = None
    app: str | None = None
    version: str | None = None
    name: str | None = None
    arg_matches: list[rtypes.PortMatch] | None = None
    return_matches: list[rtypes.PortMatch] | None = None
    protocols: list[str] | None = None
    force_arg_length: int | None = None
    force_return_length: int | None = None
    pure: bool | None = None
    idempotent: bool | None = None
    stateful: bool | None = None


class StateDemandModel(BaseModel):
    """Pure matching criteria for a state — mirrors ``StateDemandInputModel``."""

    hash: Optional[str] = Field(default=None, description="The exact hash of the state definition.")
    key: Optional[str] = Field(default=None, description="The state's identity key on the agent.")
    app: Optional[str] = Field(default=None, description="The identifier of the app providing the state.")
    matches: Optional[list[rmodels.PortMatchModel]] = Field(default=None, description="The matches the state definition's ports must satisfy.")
    protocols: Optional[list[str]] = Field(default=None, description="Protocols (by name) the state must implement.")


@pydantic.type(StateDemandModel, description="Pure matching criteria for a state (app/key preferred; matches loosen).")
class StateDemand:
    hash: rscalars.ActionHash | None = None
    key: str | None = None
    app: str | None = None
    matches: list[rtypes.PortMatch] | None = None
    protocols: list[str] | None = None


class ActionDependencyModel(BaseModel):
    """A named action requirement of a dependency — mirrors ``ActionDependencyInputModel``."""

    key: str = Field(description="The local slot key of this action requirement.")
    description: Optional[str] = Field(default=None, description="A description of the dependency.")
    optional: bool = Field(default=False, description="Whether the dependency is optional.")
    demand: Optional[ActionDemandModel] = Field(default=None, description="The matching criteria the resolved action must satisfy.")


@pydantic.type(ActionDependencyModel, description="A named action requirement of a dependency: a local slot key mapped to the demand the resolved action must satisfy.")
class ActionDependency:
    key: str
    description: str | None = None
    optional: bool = False
    demand: ActionDemand | None = None


class StateDependencyModel(BaseModel):
    """A named state requirement of a dependency — mirrors ``StateDependencyInputModel``."""

    key: str = Field(description="The local slot key of this state requirement.")
    description: Optional[str] = Field(default=None, description="A description of the dependency.")
    optional: bool = Field(default=False, description="Whether the dependency is optional.")
    demand: Optional[StateDemandModel] = Field(default=None, description="The matching criteria the agent's state must satisfy.")


@pydantic.type(StateDependencyModel, description="A named state requirement of a dependency: a local slot key mapped to the demand the agent's state must satisfy.")
class StateDependency:
    key: str
    description: str | None = None
    optional: bool = False
    demand: StateDemand | None = None


class DynamicValueModel(BaseModel):
    """Base model for a dynamic value input, which can reference a variable in a Blok state instance.

    Attributes:
        literal: An optional static fallback literal value, passed as a serialized string or JSON primitive.
    """

    literal: str | None = None
    path: str | None = None
