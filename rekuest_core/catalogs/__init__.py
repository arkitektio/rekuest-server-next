"""The base catalog: pure operations every UI implements for port calls.

``base_v1.json`` is the source of truth. It ships with the server (the Dockerfile copies the
whole tree) and is vendored byte-for-byte by the Python client, so both sides resolve
positional call arguments against the same parameter names. The base catalog is virtual:
it is never a ``UICatalog`` row, it is merged under every named catalog, and UI apps may
not redefine its operation names.
"""

import functools
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, model_validator
from typing_extensions import Self

from rekuest_core.inputs.models import CatalogOperationInputModel, _check_unique

BASE_CATALOG_NAME = "base"
BASE_CATALOG_VERSION = 1
BASE_CATALOG_ID = f"{BASE_CATALOG_NAME}@{BASE_CATALOG_VERSION}"
"""How the base catalog is referred to (``base@1``). Definitions may name it explicitly; it is always applied."""


def base_version_named(name: str) -> int | None:
    """The base version a catalog name refers to: ``base`` -> current, ``base@3`` -> 3, other names -> None."""
    if name == BASE_CATALOG_NAME:
        return BASE_CATALOG_VERSION
    prefix = f"{BASE_CATALOG_NAME}@"
    if name.startswith(prefix) and name[len(prefix) :].isdigit():
        return int(name[len(prefix) :])
    return None
_MANIFEST = Path(__file__).with_name("base_v1.json")


class BaseCatalogModel(BaseModel):
    """The parsed manifest."""

    name: Literal["base"]
    version: int
    description: str | None = None
    operations: list[CatalogOperationInputModel] = Field(default_factory=list)

    @model_validator(mode="after")
    def check_unique_operations(self) -> Self:
        """Operation names are unique."""
        _check_unique(self.operations, "name", "base catalog")
        return self


@functools.lru_cache(maxsize=1)
def load_base_catalog() -> BaseCatalogModel:
    """The validated manifest (cached)."""
    return BaseCatalogModel.model_validate(json.loads(_MANIFEST.read_text(encoding="utf-8")))


@functools.lru_cache(maxsize=1)
def base_operations() -> dict[str, CatalogOperationInputModel]:
    """Base operations by name."""
    return {operation.name: operation for operation in load_base_catalog().operations}


def base_operation_names() -> frozenset[str]:
    """The names UI catalogs may not redefine."""
    return frozenset(base_operations())


# A broken manifest must fail at import (server startup), not at the first registration.
load_base_catalog()
