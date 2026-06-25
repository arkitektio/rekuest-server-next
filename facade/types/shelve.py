"""Memory and filesystem shelves and their drawers."""

from __future__ import annotations

import datetime

import strawberry
import strawberry_django

from facade import filters, models


@strawberry_django.type(models.MemoryShelve, filters=filters.MemoryShelveFilter, ordering=filters.MemoryShelveOrder, pagination=True, description="A shelve for storing memory-based resources on an agent.")
class MemoryShelve:
    id: strawberry.ID = strawberry_django.field(description="ID of the memory shelve.")
    agent: "Agent" = strawberry_django.field(description="Agent that owns this memory shelve.")
    name: str = strawberry_django.field(description="Name of the shelve.")
    description: str | None = strawberry_django.field(description="Optional description of the shelve.")
    drawers: list["MemoryDrawer"] = strawberry_django.field(description="List of memory drawers within the shelve.")


@strawberry_django.type(models.FilesystemShelve, filters=filters.FilesystemShelveFilter, pagination=True, description="Shelve on an agent for filesystem-based resources.")
class FilesystemShelve:
    id: strawberry.ID = strawberry_django.field(description="ID of the filesystem shelve.")
    drawers: list["FileDrawer"] = strawberry_django.field(description="List of file drawers in the shelve.")


@strawberry_django.type(models.FileDrawer, filters=filters.FileDrawerFilter, pagination=True, description="Represents a file-based drawer within a filesystem shelve.")
class FileDrawer:
    id: strawberry.ID = strawberry_django.field(description="ID of the file drawer.")
    resource_id: str = strawberry_django.field(description="External resource identifier.")
    agent: "Agent" = strawberry_django.field(description="Agent owning the drawer.")
    identifier: str = strawberry_django.field(description="Unique string identifying the drawer.")
    created_at: datetime.datetime = strawberry_django.field(description="Creation timestamp of the drawer.")


@strawberry_django.type(models.MemoryDrawer, filters=filters.MemoryDrawerFilter, pagination=True)
class MemoryDrawer:
    id: strawberry.ID
    resource_id: str
    shelve: "MemoryShelve"
    identifier: str
    description: str | None
    created_at: datetime.datetime

    @strawberry_django.field(description="Get the latest value stored in this drawer.")
    def label(self) -> str:
        return self.label or self.identifier + "@" + self.resource_id
