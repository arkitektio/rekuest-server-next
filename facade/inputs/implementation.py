"""Inputs for implementations and action/schema/port demands."""

import strawberry
from pydantic import BaseModel
from rekuest_core import scalars as rscalars
from rekuest_core.inputs import models as rimodels
from rekuest_core.inputs import types as ritypes
from strawberry.experimental import pydantic

from facade import enums, scalars


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
