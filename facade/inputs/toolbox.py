"""Inputs for toolboxes and shortcuts."""

from typing import Any, Dict

import strawberry
from pydantic import BaseModel
from strawberry.experimental import pydantic

from facade import scalars


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
