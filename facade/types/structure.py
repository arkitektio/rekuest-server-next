"""Structure packages, interfaces, structures and their usages."""

from __future__ import annotations

import strawberry
import strawberry_django

from facade import filters, models


@strawberry_django.type(models.StructurePackage, filters=filters.StructurePackageFilter, pagination=True, description="A package of structures.")
class StructurePackage:
    id: strawberry.ID
    key: str
    description: str | None
    version: str
    structures: list["Structure"] = strawberry_django.field(
        description="Structures that are part of this package.",
    )
    interfaces: list["Interface"] = strawberry_django.field(
        description="Interfaces that are part of this package.",
    )


@strawberry_django.type(models.Interface, filters=filters.InterfaceFilter, pagination=True, description="If this structure is the default in its package.")
class Interface:
    id: strawberry.ID
    key: str
    description: str | None
    package: StructurePackage
    implementations: list[Implementation] = strawberry_django.field(description="Implementations that implement this interface.")
    output_usages: list["OutputInterfaceUsage"] = strawberry_django.field(
        description="Usages of this interface as an output in actions.",
    )
    input_usages: list["InputInterfaceUsage"] = strawberry_django.field(
        description="Usages of this interface as an input in actions.",
    )


@strawberry_django.type(models.Structure, filters=filters.StructureFilter, pagination=True, description="A strucssture representing a data schema or type.")
class Structure:
    id: strawberry.ID
    key: strawberry.ID
    package: StructurePackage
    description: str | None
    implements: list[Interface] = strawberry_django.field(
        description="Interfaces that this structure implements.",
    )
    output_usages: list["OutputStructureUsage"] = strawberry_django.field(
        description="Usages of this structure as an output in actions.",
    )
    input_usages: list["InputStructureUsage"] = strawberry_django.field(
        description="Usages of this structure as an input in actions.",
    )

    @strawberry_django.field(description="The object ID that this structure represents.")
    def identifier(self) -> strawberry.ID:
        return f"@{self.package.key}/{self.key}"

    @strawberry_django.field(description="Get the query to retrieve data for this structure.")
    def get_query(self) -> str | None:
        return self.get_query

    @strawberry_django.field(description="Get the query to describe the schema of this structure.")
    def describe_query(self) -> str | None:
        return self.describe_query


@strawberry_django.type(models.InputStructureUsage, filters=filters.InputStructureUsageFilter, pagination=True, description="Usage of an input structure in an action.")
class InputStructureUsage:
    id: strawberry.ID
    structure: Structure
    action: Action
    port_index: int
    port_key: str
    modifiers: list[str]


@strawberry_django.type(models.OutputStructureUsage, filters=filters.OutputStructureUsageFilter, pagination=True, description="Usage of an output structure in an action.")
class OutputStructureUsage:
    id: strawberry.ID
    structure: Structure
    action: Action
    port_index: int
    port_key: str
    modifiers: list[str]


@strawberry_django.type(models.InputInterfaceUsage, filters=filters.InputInterfaceUsageFilter, pagination=True, description="Usage of an input interface in an action.")
class InputInterfaceUsage:
    id: strawberry.ID
    interface: Interface
    action: Action
    port_index: int
    port_key: str
    modifiers: list[str]


@strawberry_django.type(models.OutputInterfaceUsage, filters=filters.OutputInterfaceUsageFilter, pagination=True, description="Usage of an output interface in an action.")
class OutputInterfaceUsage:
    id: strawberry.ID
    interface: Interface
    action: Action
    port_index: int
    port_key: str
    modifiers: list[str]
