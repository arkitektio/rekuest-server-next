"""Structure packages, interfaces, structures and their port-row-backed usages.

Usage lookups ("which actions consume @mikro/image?") are answered directly from the
relational ArgPort/ReturnPort rows via their indexed ``identifier`` — there is no separate
usage table. ``modifiers`` (container nesting like ``["list"]``) are reconstructed from the
materialized ``key_path``: every dot-prefix of a row's path is an ancestor row, so one extra
query fetches all ancestors for all usages.
"""

from __future__ import annotations

import strawberry
import strawberry_django

from facade import filters, models


@strawberry.type(description="A usage of a structure or interface by an action's port, derived from the relational port rows.")
class PortUsage:
    action: Action
    port_key: str = strawberry.field(description="The key of the root port this usage sits under.")
    index: int = strawberry.field(description="The index of the root port this usage sits under.")
    key_path: str = strawberry.field(description="The full dot-notation path of the using port, e.g. 'masks.mask'.")
    modifiers: list[str] = strawberry.field(description="Container nesting between the root port and the using port, e.g. ['dict', 'list'].")


def _port_usages(identifier: str, kind: str, port_model: type[models.ArgPort] | type[models.ReturnPort]) -> list[PortUsage]:
    """All usages of ``identifier`` (case-insensitive) among ports of ``kind`` in one table."""
    rows = list(port_model.objects.filter(identifier__iexact=identifier, kind=kind).select_related("action"))
    if not rows:
        return []

    action_ids = {row.action_id for row in rows}
    ancestor_paths = {".".join(row.key_path.split(".")[:depth]) for row in rows for depth in range(1, len(row.key_path.split(".")))}
    ancestors = {(port.action_id, port.key_path): port for port in port_model.objects.filter(action_id__in=action_ids, key_path__in=ancestor_paths)} if ancestor_paths else {}

    usages = []
    for row in rows:
        parts = row.key_path.split(".")
        chain = [ancestors.get((row.action_id, ".".join(parts[:depth]))) for depth in range(1, len(parts))]
        root = chain[0] if chain and chain[0] is not None else row
        usages.append(
            PortUsage(
                action=row.action,
                port_key=root.key,
                index=root.index,
                key_path=row.key_path,
                modifiers=[ancestor.kind.lower() for ancestor in chain if ancestor is not None and ancestor.kind in ("DICT", "LIST")],
            )
        )
    return usages


@strawberry_django.type(models.StructurePackage, filters=filters.StructurePackageFilter, pagination=True, description="A package of structures.")
class StructurePackage:
    id: strawberry.ID
    key: str
    description: str | None
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

    @strawberry_django.field(description="Usages of this interface as an input in actions (derived from the relational arg ports).")
    def input_usages(self) -> list[PortUsage]:
        return _port_usages(f"@{self.package.key}/{self.key}", "INTERFACE", models.ArgPort)

    @strawberry_django.field(description="Usages of this interface as an output in actions (derived from the relational return ports).")
    def output_usages(self) -> list[PortUsage]:
        return _port_usages(f"@{self.package.key}/{self.key}", "INTERFACE", models.ReturnPort)


@strawberry_django.type(models.Structure, filters=filters.StructureFilter, pagination=True, description="A strucssture representing a data schema or type.")
class Structure:
    id: strawberry.ID
    key: strawberry.ID
    package: StructurePackage
    description: str | None
    implements: list[Interface] = strawberry_django.field(
        description="Interfaces that this structure implements.",
    )

    @strawberry_django.field(description="Usages of this structure as an input in actions (derived from the relational arg ports).")
    def input_usages(self) -> list[PortUsage]:
        return _port_usages(f"@{self.package.key}/{self.key}", "STRUCTURE", models.ArgPort)

    @strawberry_django.field(description="Usages of this structure as an output in actions (derived from the relational return ports).")
    def output_usages(self) -> list[PortUsage]:
        return _port_usages(f"@{self.package.key}/{self.key}", "STRUCTURE", models.ReturnPort)

    @strawberry_django.field(description="The object ID that this structure represents.")
    def identifier(self) -> strawberry.ID:
        return f"@{self.package.key}/{self.key}"

    @strawberry_django.field(description="Get the query to retrieve data for this structure.")
    def get_query(self) -> str | None:
        return self.get_query

    @strawberry_django.field(description="Get the query to describe the schema of this structure.")
    def describe_query(self) -> str | None:
        return self.describe_query
