"""Derived Action state is reconciled on re-registration, not accumulated.

Protocols feed the matching engine (protocol demands in facade.managers), so a stale row —
an action that stopped being a predicate — must stop matching, exactly like the relational
port rows are rebuilt. Same reconciliation applies to is_test_for, which now accepts
structured targets: by exact hash, or by (app?, key, version?) with the agent's own app and
all versions as defaults; unresolvable targets are skipped instead of aborting the atomic
registration.
"""

import pytest

from rekuest_core.inputs.models import ImplementationInputModel

from facade import models
from facade.mutations.implementation import _create_implementation

from tests.factories import create_agent_for_registry, create_registry_bundle


def _impl(interface, returns_kind="BOOL", version="1", is_test_for=None):
    return ImplementationInputModel.model_validate(
        {
            "interface": interface,
            "definition": {
                "key": interface,
                "version": version,
                "name": interface.title(),
                "kind": "FUNCTION",
                "args": [{"key": "x", "kind": "INT", "nullable": False}],
                "returns": [{"key": "out", "kind": returns_kind, "nullable": False}],
                "is_test_for": is_test_for or [],
            },
        }
    )


def _agent(prefix):
    user, _, org, caller = create_registry_bundle(prefix)
    return create_agent_for_registry(caller, user, org, prefix)


@pytest.mark.django_db
def test_stale_protocol_is_removed_when_definition_stops_matching():
    agent = _agent("proto-recon")

    action = _create_implementation(_impl("checker", returns_kind="BOOL"), agent).action
    assert set(action.protocols.values_list("name", flat=True)) == {"predicate"}

    # The action stops being a predicate: the stale protocol row must not keep matching.
    action = _create_implementation(_impl("checker", returns_kind="INT"), agent).action
    assert set(action.protocols.values_list("name", flat=True)) == set()


@pytest.mark.django_db
def test_is_test_for_by_hash_and_by_key_pair():
    agent = _agent("testfor")

    target_v1 = _create_implementation(_impl("segment", version="1"), agent).action
    target_v2 = _create_implementation(_impl("segment2", version="2"), agent).action

    # By key (own app default, all versions of that key) and by exact hash.
    test_action = _create_implementation(
        _impl("segment_test", is_test_for=[{"key": "segment"}, {"hash": target_v2.hash}]),
        agent,
    ).action

    assert set(test_action.is_test_for.all()) == {target_v1, target_v2}


@pytest.mark.django_db
def test_is_test_for_version_pins_and_missing_targets_are_skipped():
    agent = _agent("testfor-pin")

    _create_implementation(_impl("proc", version="1"), agent)
    target_v2 = _create_implementation(_impl("proc2", version="2"), agent).action
    # Give both versions the same key so version pinning has something to disambiguate.
    models.Action.objects.filter(pk=target_v2.pk).update(key="proc")
    target_v2.refresh_from_db()

    test_action = _create_implementation(
        _impl(
            "proc_test",
            is_test_for=[
                {"key": "proc", "version": "2"},
                {"key": "does_not_exist"},  # skipped with a warning, not an abort
                {"hash": "no-such-hash"},
            ],
        ),
        agent,
    ).action

    assert set(test_action.is_test_for.all()) == {target_v2}


@pytest.mark.django_db
def test_is_test_for_is_reconciled_on_redeclare():
    agent = _agent("testfor-recon")
    target = _create_implementation(_impl("base", version="1"), agent).action

    test_action = _create_implementation(_impl("base_test", is_test_for=[{"key": "base"}]), agent).action
    assert set(test_action.is_test_for.all()) == {target}

    # Redeclaring without the target drops the link (set semantics, not add-only).
    test_action = _create_implementation(_impl("base_test", is_test_for=[]), agent).action
    assert set(test_action.is_test_for.all()) == set()
