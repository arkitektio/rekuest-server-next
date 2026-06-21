"""Inputs for implementations and action/schema/port demands."""

from typing import Annotated, Optional

import strawberry
from pydantic import BaseModel, Field
from rekuest_core import enums as renums
from rekuest_core import scalars as rscalars
from rekuest_core.inputs import models as rimodels
from rekuest_core.inputs import types as ritypes
from strawberry.experimental import pydantic

from facade import enums


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


@strawberry.input(description="A single runtime descriptor key/value pair carried by a candidate object.")
class DescriptorInput:
    key: str = strawberry.field(description="The descriptor key, e.g. 'axes'.")
    value: rscalars.Arg = strawberry.field(description="The descriptor value. Any JSON-serializable value.")


@strawberry.input(
    description="""A match against a concrete runtime object.

    Mirrors the structural targeting of ``PortMatchInput`` (at / key / kind / identifier /
    nullable / children) but additionally carries the object's runtime ``descriptors``. The
    descriptors are evaluated against a port's compiled ``requires`` micro-constraint, so this
    finds actions a concrete object can actually be passed to (not just structurally compatible).
    """,
)
class ObjectMatchInput:
    at: int | None = strawberry.field(default=None, description="The index of the port to match.")
    key: str | None = strawberry.field(default=None, description="The key of the port to match.")
    kind: renums.PortKind | None = strawberry.field(default=None, description="The kind of the port to match.")
    identifier: str | None = strawberry.field(default=None, description="The identifier of the port to match.")
    nullable: bool | None = strawberry.field(default=None, description="Whether the port is nullable.")
    descriptors: list[DescriptorInput] | None = strawberry.field(
        default=None,
        description="The runtime descriptors of the candidate object, matched against the port's compiled requires.",
    )
    children: Optional[list[Annotated["ObjectMatchInput", strawberry.lazy(__name__)]]] = strawberry.field(
        default=None,
        description="The matches for the children of the port to match.",
    )


@strawberry.input(description="A demand expressed as concrete runtime objects to find actions that accept them.")
class ObjectDemandInput:
    kind: enums.DemandKind = strawberry.field(description="The kind of the demand. You can ask for args or returns.")
    matches: list[ObjectMatchInput] | None = strawberry.field(default=None, description="The object matches of the demand.")
    force_length: int | None = strawberry.field(
        default=None,
        description="Require that the action has a specific number of ports.",
    )
    force_non_nullable_length: int | None = strawberry.field(
        default=None,
        description="Require that the action has a specific number of non-nullable ports.",
    )
    force_structure_length: int | None = strawberry.field(
        default=None,
        description="Require that the action has a specific number of structure ports.",
    )


@strawberry.input(description="The input for creating a action demand.")
class ActionDemandInput:
    hash: rscalars.ActionHash | None = strawberry.field(
        default=None,
        description="The hash of the action. This is used to identify the action in the system.",
    )
    name: str | None = strawberry.field(
        default=None,
        description="The name of the action. This is used to identify the action in the system.",
    )
    arg_matches: list[ritypes.PortMatchInput] | None = strawberry.field(
        default=None,
        description="The demands for the action args and returns. This is used to identify the demand in the system.",
    )
    return_matches: list[ritypes.PortMatchInput] | None = strawberry.field(
        default=None,
        description="The demands for the action args and returns. This is used to identify the demand in the system.",
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
    matches: list[ritypes.PortMatchInput] | None = strawberry.field(
        default=None,
        description="The demands for the action args and returns. This is used to identify the demand in the system.",
    )


class CreateImplementationInputModel(BaseModel):
    """Base model for creating an implementation.

    Attributes:
        implementation: Implementation configuration data
    """

    implementation: rimodels.ImplementationInputModel = Field(description="The implementation to create. This is used to identify the implementation in the system.")


@pydantic.input(
    CreateImplementationInputModel,
    description="The input for creating a implementation.",
)
class CreateImplementationInput:
    implementation: ritypes.ImplementationInput


class DeleteImplementationInputModel(BaseModel):
    """Base model for deleting an implementation.

    Attributes:
        implementation: ID of the implementation to delete
    """

    implementation: str = Field(description="The implementation ID to delete. This is used to identify the implementation in the system.")


@pydantic.input(
    DeleteImplementationInputModel,
    description="The input for deleting a implementation.",
)
class DeleteImplementationInput:
    implementation: strawberry.ID
