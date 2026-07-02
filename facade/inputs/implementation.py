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
