"""Virtual structure/interface/package types, derived entirely from the port rows.

There is no catalog table: a "structure" is nothing more than a distinct ``@package/key``
identifier referenced by some action's port. The types here are plain strawberry types
(no Django model, no DB id — the identifier IS the identity), enumerated from the indexed
``identifier`` column of the relational ArgPort/ReturnPort rows and scoped to the
requesting organization. Registration writes nothing; the enumeration can never drift
from what ports actually reference.

Usage lookups ("which actions consume @mikro/image?") are likewise answered from the port
rows. ``modifiers`` (container nesting like ``["list"]``) are reconstructed from the
materialized ``key_path``: every dot-prefix of a row's path is an ancestor row, so one
extra query fetches all ancestors for all usages.
"""

from __future__ import annotations

import strawberry
from asgiref.sync import sync_to_async
from strawberry.types import Info

from facade import models


@strawberry.type(description="A usage of a structure or interface by an action's port, derived from the relational port rows.")
class PortUsage:
    action: Action
    port_key: str = strawberry.field(description="The key of the root port this usage sits under.")
    index: int = strawberry.field(description="The index of the root port this usage sits under.")
    key_path: str = strawberry.field(description="The full dot-notation path of the using port, e.g. 'masks.mask'.")
    modifiers: list[str] = strawberry.field(description="Container nesting between the root port and the using port, e.g. ['dict', 'list'].")


def _port_usages(info: Info, identifier: str, kind: str, port_model: type[models.ArgPort] | type[models.ReturnPort]) -> list[PortUsage]:
    """All usages of ``identifier`` (case-insensitive) among ports of ``kind`` in one table, scoped to the requesting org."""
    rows = list(port_model.objects.filter(identifier__iexact=identifier, kind=kind, action__organization=info.context.request.organization).select_related("action"))
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


def _distinct_identifiers(info: Info, kind: str, search: str | None = None, package_key: str | None = None) -> list[str]:
    """Distinct (lowercased) '@package/key' identifiers of ``kind`` referenced by the org's ports."""
    identifiers: set[str] = set()
    for port_model in (models.ArgPort, models.ReturnPort):
        queryset = port_model.objects.filter(kind=kind, identifier__isnull=False, action__organization=info.context.request.organization)
        if search:
            queryset = queryset.filter(identifier__icontains=search)
        if package_key:
            queryset = queryset.filter(identifier__istartswith=f"@{package_key}/")
        identifiers.update(queryset.values_list("identifier", flat=True).distinct())
    # Identifiers without a package part ('@pkg/key') were never catalogued; keep that rule.
    return sorted({identifier.lower() for identifier in identifiers if "/" in identifier})


def _package_of(identifier: str) -> str:
    return identifier.split("/")[0].removeprefix("@")


def _key_of(identifier: str) -> str:
    return identifier.split("/")[-1]


@strawberry.type(description="A package of structures/interfaces, derived from the '@package/' prefix of port identifiers.")
class StructurePackage:
    key: strawberry.ID = strawberry.field(description="The package key (the part between '@' and '/').")

    @strawberry.field(description="Structures of this package referenced by the org's ports.")
    async def structures(self, info: Info) -> list["Structure"]:
        identifiers = await sync_to_async(_distinct_identifiers)(info, "STRUCTURE", package_key=self.key)
        return [Structure(identifier=identifier) for identifier in identifiers]

    @strawberry.field(description="Interfaces of this package referenced by the org's ports.")
    async def interfaces(self, info: Info) -> list["Interface"]:
        identifiers = await sync_to_async(_distinct_identifiers)(info, "INTERFACE", package_key=self.key)
        return [Interface(identifier=identifier) for identifier in identifiers]


@strawberry.type(description="An interface referenced by an action's port, derived from the relational port rows.")
class Interface:
    identifier: strawberry.ID = strawberry.field(description="The full identifier, e.g. '@rekuest/taskevent'.")

    @strawberry.field(description="The local key (the part after '/').")
    def key(self) -> str:
        return _key_of(self.identifier)

    @strawberry.field(description="The package this interface belongs to.")
    def package(self) -> StructurePackage:
        return StructurePackage(key=_package_of(self.identifier))

    @strawberry.field(description="Usages of this interface as an input in actions (derived from the relational arg ports).")
    async def input_usages(self, info: Info) -> list[PortUsage]:
        return await sync_to_async(_port_usages)(info, self.identifier, "INTERFACE", models.ArgPort)

    @strawberry.field(description="Usages of this interface as an output in actions (derived from the relational return ports).")
    async def output_usages(self, info: Info) -> list[PortUsage]:
        return await sync_to_async(_port_usages)(info, self.identifier, "INTERFACE", models.ReturnPort)


@strawberry.type(description="A structure (data type) referenced by an action's port, derived from the relational port rows.")
class Structure:
    identifier: strawberry.ID = strawberry.field(description="The full identifier, e.g. '@mikro/image'.")

    @strawberry.field(description="The local key (the part after '/').")
    def key(self) -> str:
        return _key_of(self.identifier)

    @strawberry.field(description="The package this structure belongs to.")
    def package(self) -> StructurePackage:
        return StructurePackage(key=_package_of(self.identifier))

    @strawberry.field(description="Usages of this structure as an input in actions (derived from the relational arg ports).")
    async def input_usages(self, info: Info) -> list[PortUsage]:
        return await sync_to_async(_port_usages)(info, self.identifier, "STRUCTURE", models.ArgPort)

    @strawberry.field(description="Usages of this structure as an output in actions (derived from the relational return ports).")
    async def output_usages(self, info: Info) -> list[PortUsage]:
        return await sync_to_async(_port_usages)(info, self.identifier, "STRUCTURE", models.ReturnPort)


# --------------------------------------------------------------------------- #
# Query resolvers (wired in facade/schema.py)
# --------------------------------------------------------------------------- #
async def list_structures(info: Info, search: str | None = None) -> list[Structure]:
    identifiers = await sync_to_async(_distinct_identifiers)(info, "STRUCTURE", search=search)
    return [Structure(identifier=identifier) for identifier in identifiers]


async def list_interfaces(info: Info, search: str | None = None) -> list[Interface]:
    identifiers = await sync_to_async(_distinct_identifiers)(info, "INTERFACE", search=search)
    return [Interface(identifier=identifier) for identifier in identifiers]


def _known_packages(info: Info) -> set[str]:
    return {_package_of(identifier) for kind in ("STRUCTURE", "INTERFACE") for identifier in _distinct_identifiers(info, kind)}


async def list_structure_packages(info: Info, search: str | None = None) -> list[StructurePackage]:
    packages = await sync_to_async(_known_packages)(info)
    if search:
        packages = {package for package in packages if search.lower() in package.lower()}
    return [StructurePackage(key=key) for key in sorted(packages)]


async def get_structure(info: Info, identifier: strawberry.ID) -> Structure:
    if str(identifier).lower() not in await sync_to_async(_distinct_identifiers)(info, "STRUCTURE"):
        raise ValueError(f"No action port references the structure {identifier!r}")
    return Structure(identifier=str(identifier).lower())


async def get_interface(info: Info, identifier: strawberry.ID) -> Interface:
    if str(identifier).lower() not in await sync_to_async(_distinct_identifiers)(info, "INTERFACE"):
        raise ValueError(f"No action port references the interface {identifier!r}")
    return Interface(identifier=str(identifier).lower())


async def get_structure_package(info: Info, key: strawberry.ID) -> StructurePackage:
    known = await sync_to_async(_known_packages)(info)
    if str(key) not in known:
        raise ValueError(f"No action port references the package {key!r}")
    return StructurePackage(key=str(key))
