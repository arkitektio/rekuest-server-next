"""Inputs for registering UI catalogs."""

import strawberry
from pydantic import BaseModel, Field, model_validator
from strawberry.experimental import pydantic
from typing_extensions import Self

from rekuest_core.inputs import models as rimodels
from rekuest_core.inputs import types as ritypes


class RegisterUiCatalogInputModel(BaseModel):
    """What a UI app can render and evaluate, upserted by name within the caller's organization."""

    name: str = Field(min_length=1, description="The catalog name. Bloks and definitions reference it by this name; registering again replaces the previous components and operations.")
    description: str | None = Field(default=None, description="Human-readable description of the catalog.")
    components: list[rimodels.CatalogComponentInputModel] = Field(default_factory=list, description="The components this catalog can render.")
    operations: list[rimodels.CatalogOperationInputModel] = Field(default_factory=list, description="The pure operations this catalog can evaluate for UtilCalls.")
    widget_defaults: list[rimodels.WidgetDefaultInputModel] = Field(
        default_factory=list,
        description="Default widgets per port kind and/or structure identifier. A UI renders them for ports that declare no widget; an identifier match beats a kind match. Each widget is validated against this catalog plus base at registration.",
    )

    @model_validator(mode="after")
    def check_unique_selectors(self) -> Self:
        """Two defaults may not target the same (kind, identifier)."""
        seen: set[tuple[str | None, str | None]] = set()
        for default in self.widget_defaults:
            if default.selector in seen:
                raise ValueError(f"widget_defaults: duplicate selector kind={default.selector[0]!r} identifier={default.selector[1]!r}")
            seen.add(default.selector)
        return self


@pydantic.input(RegisterUiCatalogInputModel, description="Register (upsert by name, scoped to the caller's organization) the components and operations a UI app can render and evaluate.")
class RegisterUiCatalogInput:
    name: str
    description: str | None = None
    components: list[ritypes.CatalogComponentInput] = strawberry.field(default_factory=list)
    operations: list[ritypes.CatalogOperationInput] = strawberry.field(default_factory=list)
    widget_defaults: list[ritypes.WidgetDefaultInput] = strawberry.field(default_factory=list)
