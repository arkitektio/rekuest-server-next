"""Registration write-path efficiency and safety.

Pins the three write-path properties: relational ports are bulk-created level-by-level
(query count scales with tree DEPTH, not port count), reconnecting with an unchanged
definition hash skips the rebuild entirely (while legacy actions missing relational state
are still healed), and ``_create_implementation`` is atomic — a mid-flight failure leaves
no partial Action/port rows behind.
"""

import pytest

from rekuest_core.inputs.models import ImplementationInputModel

from facade import models
from facade.mutations import implementation as impl_module
from facade.mutations.implementation import _create_implementation, rebuild_relational_ports

from tests.factories import create_agent_for_registry, create_registry_bundle


def _definition(extra_arg=False):
    args = [
        {
            "key": "options",
            "kind": "DICT",
            "nullable": False,
            "children": [
                {"key": "alpha", "kind": "INT", "nullable": False},
                {"key": "beta", "kind": "INT", "nullable": False},
                {"key": "gamma", "kind": "INT", "nullable": False},
                {"key": "delta", "kind": "INT", "nullable": False},
                {"key": "nested", "kind": "DICT", "nullable": False, "children": [{"key": "deep", "kind": "INT", "nullable": False}]},
            ],
        },
        {"key": "image", "kind": "STRUCTURE", "identifier": "@mikro/image", "nullable": False},
    ]
    if extra_arg:
        args.append({"key": "n", "kind": "INT", "nullable": False})
    return {
        "key": "writepath",
        "version": "1",
        "name": "Writepath",
        "kind": "FUNCTION",
        "args": args,
        "returns": [{"key": "count", "kind": "INT", "nullable": False}],
    }


def _implementation_input(extra_arg=False):
    return ImplementationInputModel.model_validate({"interface": "writepath", "definition": _definition(extra_arg=extra_arg)})


def _agent(prefix):
    user, _, org, caller = create_registry_bundle(prefix)
    return create_agent_for_registry(caller, user, org, prefix)


@pytest.mark.django_db
def test_rebuild_query_count_scales_with_depth_not_ports(django_assert_max_num_queries):
    agent = _agent("wp-depth")
    implementation = _create_implementation(_implementation_input(), agent)
    action = implementation.action
    definition = _implementation_input().definition

    # 9 total port rows across depth 3 (args) + depth 1 (returns): the bulk path needs one
    # INSERT per level per table (3 + 1), plus Django's delete-cascade collector (3 per table)
    # and the counts update = 11 — below the old one-INSERT-per-port floor (9 inserts + 6
    # delete queries + update = 16), and constant in port count for a fixed depth.
    with django_assert_max_num_queries(11):
        rebuild_relational_ports(action, definition)

    assert action.arg_ports.count() == 8
    assert action.return_ports.count() == 1
    assert action.arg_ports.get(key_path="options.nested.deep").kind == "INT"


@pytest.mark.django_db
def test_reconnect_same_definition_skips_rebuild(monkeypatch, django_assert_max_num_queries):
    agent = _agent("wp-skip")
    first = _create_implementation(_implementation_input(), agent)
    port_ids = set(first.action.arg_ports.values_list("id", flat=True))
    assert port_ids

    rebuild_calls = []
    monkeypatch.setattr(impl_module, "rebuild_relational_ports", lambda *a, **k: rebuild_calls.append(a))
    catalog_calls = []
    monkeypatch.setattr(impl_module, "register_catalog_entities", lambda *a, **k: catalog_calls.append(a))

    # Reconnect with the identical definition: same hash, so the whole derived-state block skips.
    with django_assert_max_num_queries(15):
        second = _create_implementation(_implementation_input(), agent)

    assert second.action.pk == first.action.pk
    assert not rebuild_calls
    assert not catalog_calls
    assert set(second.action.arg_ports.values_list("id", flat=True)) == port_ids


@pytest.mark.django_db
def test_changed_definition_still_rebuilds():
    agent = _agent("wp-change")
    first = _create_implementation(_implementation_input(), agent)
    old_hash = first.action.hash
    old_port_ids = set(first.action.arg_ports.values_list("id", flat=True))

    second = _create_implementation(_implementation_input(extra_arg=True), agent)

    assert second.action.pk == first.action.pk
    assert second.action.hash != old_hash
    assert second.action.arg_count == 3
    # Rebuild replaced the rows (delete-then-recreate), so no old row survives.
    assert not old_port_ids & set(second.action.arg_ports.values_list("id", flat=True))


@pytest.mark.django_db
def test_legacy_action_without_port_rows_is_healed():
    agent = _agent("wp-heal-rows")
    action = _create_implementation(_implementation_input(), agent).action

    # Simulate a pre-relational-engine action: rows gone, counts stale but matching.
    action.arg_ports.all().delete()
    action.return_ports.all().delete()

    healed = _create_implementation(_implementation_input(), agent).action
    assert healed.arg_ports.count() == 8
    assert healed.return_ports.count() == 1


@pytest.mark.django_db
def test_legacy_action_with_stale_counts_is_healed():
    agent = _agent("wp-heal-counts")
    action = _create_implementation(_implementation_input(), agent).action

    # Counts diverged (e.g. written before arg_count existed, defaulting to 0).
    models.Action.objects.filter(pk=action.pk).update(arg_count=0, return_count=0)

    healed = _create_implementation(_implementation_input(), agent).action
    assert healed.arg_count == 2
    assert healed.return_count == 1
    assert healed.arg_ports.filter(parent__isnull=True).count() == 2


@pytest.mark.django_db
def test_structure_usages_derived_from_port_rows():
    """Registration creates the catalog entities; usage lookups are derived from the relational
    port rows (identifier + parent-chain modifiers), with output/input direction taken from the
    table the row lives in."""
    from facade.types.structure import _port_usages

    user, _, org, caller = create_registry_bundle("wp-usages")
    agent = create_agent_for_registry(caller, user, org, "wp-usages")
    implementation = _create_implementation(
        ImplementationInputModel.model_validate(
            {
                "interface": "masker",
                "definition": {
                    "key": "masker",
                    "version": "1",
                    "name": "Masker",
                    "kind": "FUNCTION",
                    "args": [{"key": "image", "kind": "STRUCTURE", "identifier": "@mikro/image", "nullable": False}],
                    "returns": [
                        {
                            "key": "masks",
                            "kind": "LIST",
                            "nullable": False,
                            "children": [{"key": "mask", "kind": "STRUCTURE", "identifier": "@mikro/mask"}],
                        }
                    ],
                },
            }
        ),
        agent,
    )
    action = implementation.action

    # Catalog entities registered (lower-cased keys).
    assert models.Structure.objects.filter(package__key="mikro", key="mask").exists()
    assert models.Structure.objects.filter(package__key="mikro", key="image").exists()

    # The nested return structure is an OUTPUT usage with the container chain as modifiers.
    output_usages = _port_usages("@mikro/mask", "STRUCTURE", models.ReturnPort)
    assert len(output_usages) == 1
    assert output_usages[0].action.pk == action.pk
    assert output_usages[0].modifiers == ["list"]
    assert output_usages[0].port_key == "masks"
    assert output_usages[0].key_path == "masks.mask"
    # ...and NOT an input usage (regression: nested outputs used to land on the input side).
    assert _port_usages("@mikro/mask", "STRUCTURE", models.ArgPort) == []

    # The genuine input structure is an input usage; lookup is case-insensitive.
    input_usages = _port_usages("@MIKRO/IMAGE", "STRUCTURE", models.ArgPort)
    assert len(input_usages) == 1
    assert input_usages[0].modifiers == []
    assert input_usages[0].port_key == "image"


@pytest.mark.django_db
def test_create_implementation_is_atomic(monkeypatch):
    agent = _agent("wp-atomic")

    def boom(*args, **kwargs):
        raise RuntimeError("mid-flight failure")

    monkeypatch.setattr(impl_module, "register_catalog_entities", boom)

    with pytest.raises(RuntimeError, match="mid-flight failure"):
        _create_implementation(_implementation_input(), agent)

    # The atomic block rolled everything back: no Action, no orphaned port rows.
    assert not models.Action.objects.filter(key="writepath").exists()
    assert not models.ArgPort.objects.filter(key_path__startswith="options").exists()
    assert not models.Implementation.objects.filter(interface="writepath").exists()
