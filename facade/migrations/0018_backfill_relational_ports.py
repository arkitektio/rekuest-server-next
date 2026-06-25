"""Backfill the relational ArgPort/ReturnPort engine.

Until now the relational port rows were written but never read, and the write path appended
fresh rows on every (re)registration without purging the previous ones, so existing data may
contain duplicate/stale ports and was compiled with a buggy JSONPath compiler. Now that the
matching layer queries these tables, rebuild them cleanly from each Action's args/returns JSON:
purge old rows, recompile ``compiled_jsonpath``, and refresh the pre-calculated root counts.
"""

from types import SimpleNamespace

from django.db import migrations

from facade.descriptors import compile_descriptors_to_jsonpath


def _compile_safe(descriptors):
    """Compile a list of descriptor dicts, tolerating legacy/invalid entries."""
    if not descriptors:
        return None
    try:
        return compile_descriptors_to_jsonpath([SimpleNamespace(**d) for d in descriptors])
    except Exception as exc:  # pragma: no cover - defensive for legacy data
        print(f"backfill_relational_ports: skipping invalid descriptors {descriptors!r}: {exc}")
        return None


def _build_port(PortModel, action, port, index, parent, parent_path, descriptor_key):
    key = port.get("key")
    current_path = f"{parent_path}.{key}" if parent_path else (key or "")
    row = PortModel.objects.create(
        action=action,
        parent=parent,
        index=index,
        key=key,
        key_path=current_path,
        kind=port.get("kind"),
        identifier=port.get("identifier"),
        compiled_jsonpath=_compile_safe(port.get(descriptor_key)),
        nullable=bool(port.get("nullable") or False),
    )
    for child_index, child in enumerate(port.get("children") or []):
        _build_port(PortModel, action, child, child_index, row, current_path, descriptor_key)


def rebuild_ports(apps, schema_editor):
    Action = apps.get_model("facade", "Action")
    ArgPort = apps.get_model("facade", "ArgPort")
    ReturnPort = apps.get_model("facade", "ReturnPort")

    for action in Action.objects.all().iterator():
        ArgPort.objects.filter(action=action).delete()
        ReturnPort.objects.filter(action=action).delete()

        args = action.args or []
        returns = action.returns or []

        for index, port in enumerate(args):
            _build_port(ArgPort, action, port, index, None, "", "requires")
        for index, port in enumerate(returns):
            _build_port(ReturnPort, action, port, index, None, "", "provides")

        action.arg_count = len(args)
        action.return_count = len(returns)
        action.save(update_fields=["arg_count", "return_count"])


def noop_reverse(apps, schema_editor):
    # Rebuilding from JSON is idempotent and the rows are regenerated on every registration,
    # so there is nothing meaningful to undo.
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("facade", "0017_implementation_higher_order_config"),
    ]

    operations = [
        migrations.RunPython(rebuild_ports, noop_reverse),
    ]
