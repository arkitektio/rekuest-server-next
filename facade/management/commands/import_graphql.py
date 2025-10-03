# management/commands/import_schema_packages.py
from __future__ import annotations

import sys
import re
from pathlib import Path
from typing import List

from django.core.management.base import BaseCommand
from django.db import transaction

from graphql import parse
from graphql.language.ast import (
    DocumentNode,
    InterfaceTypeDefinitionNode,
    ObjectTypeDefinitionNode,
)

from pydantic import ValidationError

from facade import models
from rekuest_core.inputs.models import (
    StructurePackageInputModel,
)


# ---- SDL → Pydantic model ---------------------------------------------------

def sdl_to_package_model(
    sdl: str, *, package_key: str, version: str
) -> StructurePackageInputModel:
    doc: DocumentNode = parse(sdl)

    interfaces = []
    structures = []

    for defn in doc.definitions:
        if isinstance(defn, InterfaceTypeDefinitionNode):
            interfaces.append(
                {
                    "key": defn.name.value,
                    "description": defn.description.value if defn.description else None,
                }
            )

    for defn in doc.definitions:
        if isinstance(defn, ObjectTypeDefinitionNode):
            name = defn.name.value
            if name in {"Query", "Mutation", "Subscription"}:
                continue
            structures.append(
                {
                    "key": name,
                    "description": defn.description.value if defn.description else None,
                    "implements": [iface.name.value for iface in (defn.interfaces or [])],
                }
            )

    return StructurePackageInputModel(
        key=package_key,
        version=version,
        interfaces=interfaces,
        structures=structures,
    )


# ---- DB upsert --------------------------------------------------------------

def upsert_from_models(packages: List[StructurePackageInputModel]) -> None:
    
    
    
    with transaction.atomic():
        for package in packages:
            pack, _ = models.StructurePackage.objects.update_or_create(
                key=package.key.lower(),
                defaults=dict(description=getattr(package, "description", None)),
            )
            
            print("Upserting package", package.key)

            # Interfaces
            for interface in package.interfaces or []:
                models.Interface.objects.update_or_create(
                    package=pack,
                    key=interface.key.lower(),
                    defaults=dict(
                        description=getattr(interface, "description", None),
                        default_widget=(
                            interface.default_widget and interface.default_widget.model_dump_json()
                        )
                        or None,
                        default_return_widget=(
                            interface.default_return_widget
                            and interface.default_return_widget.model_dump_json()
                        )
                        or None,
                    ),
                )
                
                print("  Upserting interface", interface.key)

            # Structures
            for structure in package.structures or []:
                struc, _ = models.Structure.objects.update_or_create(
                    package=pack,
                    key=structure.key.lower(),
                    defaults=dict(
                        description=getattr(structure, "description", None),
                        default_widget=(
                            structure.default_widget and structure.default_widget.model_dump_json()
                        )
                        or None,
                        default_return_widget=(
                            structure.default_return_widget
                            and structure.default_return_widget.model_dump_json()
                        )
                        or None,
                    ),
                )
                
                print("  Upserting structure", structure.key)

                struc.implements.set(
                    models.Interface.objects.filter(
                        package=pack, key__in=(i.lower() for i in structure.implements or [])
                    )
                )
                print("    Setting implements:", structure.implements or [])
                struc.descriptors.set(
                    models.Descriptor.objects.filter(
                        package=pack, key__in=(i.lower() for i in structure.descriptors or [])
                    )
                )
                print("    Setting descriptors:", structure.descriptors or [])


# ---- Management command -----------------------------------------------------

class Command(BaseCommand):
    help = "Parse GraphQL SDL files in ./schemas into StructurePackageInputModel(s) and upsert them."

    def handle(self, *args, **options):
        schema_dir = Path("./type_schemas")
        if not schema_dir.exists():
            self.stderr.write(self.style.ERROR(f"No ./schemas directory found"))
            sys.exit(1)

        files = list(schema_dir.glob("*.graphql"))
        if not files:
            self.stderr.write(self.style.ERROR("No SDL files found in ./schemas/*.graphql"))
            sys.exit(1)

        pkg_models: List[StructurePackageInputModel] = []

        for file in files:
            # Expect filenames like key_semver_version.graphql
            # e.g. mikro_v1.graphql or analysis_1.2.3.graphql
            m = re.match(r"(?P<key>[a-zA-Z0-9\-]+)_(?P<version>[a-zA-Z0-9\.\-]+)\.graphql", file.name)
            if not m:
                self.stderr.write(self.style.WARNING(f"Skipping {file.name}: invalid filename format"))
                continue

            package_key = m.group("key")
            version = m.group("version")

            sdl = file.read_text(encoding="utf-8")
            try:
                pkg_model = sdl_to_package_model(sdl, package_key=package_key, version=version)
                pkg_models.append(pkg_model)
            except ValidationError as e:
                self.stderr.write(self.style.ERROR(f"Validation failed for {file.name}:"))
                self.stderr.write(str(e))
                sys.exit(2)

        if not pkg_models:
            self.stderr.write(self.style.ERROR("No valid SDL packages parsed."))
            sys.exit(1)

        upsert_from_models(pkg_models)

        self.stdout.write(
            self.style.SUCCESS(f"Upserted {len(pkg_models)} package(s) from ./schemas/*.graphql")
        )
