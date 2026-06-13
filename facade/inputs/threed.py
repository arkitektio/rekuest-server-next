"""Inputs for 3D models, spaces and placements."""

import strawberry
from datalayer import scalars as dscalars
from pydantic import BaseModel
from strawberry.experimental import pydantic


class CreateThreeDModelInputModel(BaseModel):
    name: str
    description: str | None = None
    media: str


@pydantic.input(CreateThreeDModelInputModel, description="The input for creating a 3D model.")
class CreateThreeDModelInput:
    name: str = strawberry.field(description="The name of the 3D model.")
    description: str | None = strawberry.field(default=None, description="A description of the 3D model.")
    media: dscalars.MediaLike = strawberry.field(description="The media store file for the 3D model.")


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
    model: strawberry.ID | None = strawberry.field(default=None, description="The three-dimensional model for the placement.")
    agent: strawberry.ID | None = strawberry.field(default=None, description="The agent ID to create the placement for. If not provided, the placement will be created for the default agent.")
    materialized_blok: strawberry.ID | None = strawberry.field(default=None, description="A specific blok that should be used to visualize the state of the placement")


@pydantic.input(UpdatePlacementInputModel, description="The input for updating a placement.")
class UpdatePlacementInput:
    id: strawberry.ID = strawberry.field(description="The ID of the placement to update.")
    role: str | None = strawberry.field(default=None, description="The new role for the placement.")
    affine_matrix: list[list[float]] | None = strawberry.field(default=None, description="The new affine matrix for the placement.")
    model: strawberry.ID | None = strawberry.field(default=None, description="The new model for the placement.")


class DeletePlacementInputModel(BaseModel):
    id: str


@pydantic.input(DeletePlacementInputModel, description="The input for deleting a placement.")
class DeletePlacementInput:
    id: strawberry.ID = strawberry.field(description="The ID of the placement to delete.")
