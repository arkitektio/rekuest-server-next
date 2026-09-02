"""Inputs for registering UI catalogs."""

import strawberry
from pydantic import BaseModel, Field
from strawberry.experimental import pydantic

from rekuest_core.inputs import models as rimodels
from rekuest_core.inputs import types as ritypes


class RegisterUiCatalogInputModel(BaseModel):
    """What a UI app can render and evaluate, upserted by name within the caller's organization."""

    name: str = Field(min_length=1, description="The catalog name. Bloks and definitions reference it by this name; registering again replaces the previous components and operations.")
    description: str | None = Field(default=None, description="Human-readable description of the catalog.")
    components: list[rimodels.CatalogComponentInputModel] = Field(default_factory=list, description="The components this catalog can render.")
    operations: list[rimodels.CatalogOperationInputModel] = Field(default_factory=list, description="The pure operations this catalog can evaluate for UtilCalls.")


@pydantic.input(RegisterUiCatalogInputModel, description="Register (upsert by name, scoped to the caller's organization) the components and operations a UI app can render and evaluate.")
class RegisterUiCatalogInput:
    name: str
    description: str | None = None
    components: list[ritypes.CatalogComponentInput] = strawberry.field(default_factory=list)
    operations: list[ritypes.CatalogOperationInput] = strawberry.field(default_factory=list)
