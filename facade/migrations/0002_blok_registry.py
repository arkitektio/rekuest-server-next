"""Blok write-path hardening and the UI catalog registry.

- ``UICatalog`` gains ``description``, ``components``, ``operations`` and ``registered_by`` and
  loses the never-used ``schema`` blob.
- ``Blok.catalog`` becomes required (the GraphQL type already declared it non-null).
- Unique constraints on the keys every write path upserts on: ``Blok(organization, name)``,
  ``BlokDependency(blok, key)``, ``UICatalog(organization, name)``.

The data step dedupes rows that would violate the new constraints (keeping the lowest id) and
backfills null ``Blok.catalog`` with the organization's ``default`` catalog, the same name
``create_blok`` uses.
"""

import django.db.models.deletion
from django.db import migrations, models
from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from django.db.migrations.state import StateApps


def dedupe_and_backfill(apps: StateApps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    """Drop rows that would violate the new unique constraints and give every blok a catalog."""
    Blok = apps.get_model("facade", "Blok")
    BlokDependency = apps.get_model("facade", "BlokDependency")
    UICatalog = apps.get_model("facade", "UICatalog")

    for model, fields in (
        (UICatalog, ("organization_id", "name")),
        (Blok, ("organization_id", "name")),
        (BlokDependency, ("blok_id", "key")),
    ):
        seen = set()
        for row in model.objects.order_by("id").values("id", *fields):
            key = tuple(row[f] for f in fields)
            if key in seen:
                model.objects.filter(id=row["id"]).delete()
            else:
                seen.add(key)

    for blok in Blok.objects.filter(catalog__isnull=True):
        blok.catalog = UICatalog.objects.get_or_create(name="default", organization_id=blok.organization_id)[0]
        blok.save(update_fields=["catalog"])


class Migration(migrations.Migration):
    """Blok constraints, required catalog, and the UI catalog registry fields."""

    dependencies = [
        ("authentikate", "0001_initial"),
        ("facade", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="uicatalog",
            name="description",
            field=models.TextField(blank=True, help_text="A description of this catalog", null=True),
        ),
        migrations.AddField(
            model_name="uicatalog",
            name="components",
            field=models.JSONField(default=list, help_text="Registered component specs (rekuest_core CatalogComponent): the names a ComponentNode.component may use and the props each accepts."),
        ),
        migrations.AddField(
            model_name="uicatalog",
            name="operations",
            field=models.JSONField(default=list, help_text="Registered operation specs (rekuest_core CatalogOperation): the names a UtilCall.operation may use, their arguments and return kind."),
        ),
        migrations.AddField(
            model_name="uicatalog",
            name="registered_by",
            field=models.ForeignKey(blank=True, help_text="The client (UI app) that last registered this catalog's components and operations.", null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="registered_ui_catalogs", to="authentikate.client"),
        ),
        migrations.RemoveField(
            model_name="uicatalog",
            name="schema",
        ),
        migrations.RunPython(dedupe_and_backfill, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="blok",
            name="catalog",
            field=models.ForeignKey(help_text="The catalog this Blok belongs to", on_delete=django.db.models.deletion.CASCADE, related_name="bloks", to="facade.uicatalog"),
        ),
        migrations.AddConstraint(
            model_name="blok",
            constraint=models.UniqueConstraint(fields=("organization", "name"), name="unique_blok_name_per_organization"),
        ),
        migrations.AddConstraint(
            model_name="blokdependency",
            constraint=models.UniqueConstraint(fields=("blok", "key"), name="unique_dependency_key_per_blok"),
        ),
        migrations.AddConstraint(
            model_name="uicatalog",
            constraint=models.UniqueConstraint(fields=("organization", "name"), name="unique_ui_catalog_name_per_organization"),
        ),
    ]
