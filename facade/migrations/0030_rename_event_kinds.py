"""Rename AssignationEventKind vocabulary in already-persisted rows.

The ``AssignationEventChoices`` values were renamed for clarity (and to fix the
INTERUPTING/INTERUPTED typo). This pure data migration rewrites the stored string values on
the two columns that hold them: ``AssignationEvent.kind`` and ``Assignation.latest_event_kind``.

Raw SQL is used on purpose: a normal ``.filter(kind="ASSIGN")`` would route the old value
through ``django_choices_field``, which coerces it via the *live* enum — and the old values
no longer exist there, so it would raise ``ValueError``. Raw UPDATEs sidestep that coercion.

Deliberately NOT rewritten: ``AssignationEvent.level`` — although it is (mis)declared with
``AssignationEventChoices``, it actually stores log levels (DEBUG/INFO/ERROR/WARN/CRITICAL),
so rewriting ``ERROR``→``FAILED`` there would corrupt log levels. ``latest_instruct_kind``
uses ``AssignationInstructChoices`` (unchanged).
"""

from django.db import migrations

# old value -> new value
RENAMES = {
    "ASSIGN": "STARTED",
    "DONE": "COMPLETED",
    "ERROR": "FAILED",
    "CANCELING": "CANCELLING",
    "INTERUPTING": "INTERRUPTING",
    "INTERUPTED": "INTERRUPTED",
}


def _apply(apps, schema_editor, mapping):
    ev_table = apps.get_model("facade", "AssignationEvent")._meta.db_table
    ass_table = apps.get_model("facade", "Assignation")._meta.db_table
    with schema_editor.connection.cursor() as cur:
        for old, new in mapping.items():
            cur.execute(f"UPDATE {ev_table} SET kind = %s WHERE kind = %s", [new, old])
            cur.execute(f"UPDATE {ass_table} SET latest_event_kind = %s WHERE latest_event_kind = %s", [new, old])


def forwards(apps, schema_editor):
    _apply(apps, schema_editor, RENAMES)


def backwards(apps, schema_editor):
    _apply(apps, schema_editor, {new: old for old, new in RENAMES.items()})


class Migration(migrations.Migration):
    dependencies = [
        ("facade", "0029_agent_active_session_id"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
