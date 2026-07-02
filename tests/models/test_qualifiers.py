"""Semantic qualifiers (pure / idempotent / is_dev) on actions.

Qualifiers are declared on the definition, persisted on the Action, and deliberately NOT
identity-bearing: they're excluded from ``unique_hash`` so flipping them never forces fleet
re-registration — instead ``_create_implementation`` syncs them unconditionally. Purity is a
strong claim, so contradictions (pure×PHYSICAL, pure×stateful) are rejected at registration
and pure auto-implies idempotent.
"""

import pytest

from rekuest_core.inputs.models import ImplementationInputModel

from facade.mutations.implementation import _create_implementation

from tests.factories import create_agent_for_registry, create_registry_bundle


def _input(pure=False, idempotent=False, is_dev=False, stateful=False, effect="NONE", name="Quali"):
    return ImplementationInputModel.model_validate(
        {
            "interface": "quali",
            "effect": effect,
            "definition": {
                "key": "quali",
                "version": "1",
                "name": name,
                "kind": "FUNCTION",
                "stateful": stateful,
                "pure": pure,
                "idempotent": idempotent,
                "is_dev": is_dev,
                "args": [{"key": "n", "kind": "INT", "nullable": False}],
                "returns": [],
            },
        }
    )


def _agent(prefix):
    user, _, org, caller = create_registry_bundle(prefix)
    return create_agent_for_registry(caller, user, org, prefix)


@pytest.mark.django_db
def test_qualifiers_persist_and_pure_implies_idempotent():
    agent = _agent("quali-persist")
    action = _create_implementation(_input(pure=True, is_dev=True), agent).action

    assert action.pure is True
    assert action.idempotent is True  # implied by pure
    assert action.is_dev is True  # regression: was declarable but never persisted


@pytest.mark.django_db
def test_qualifier_flip_syncs_without_hash_change():
    agent = _agent("quali-flip")
    first = _create_implementation(_input(idempotent=False), agent).action
    original_hash = first.hash
    assert first.idempotent is False

    # Same definition except the qualifier: identity hash must NOT change (no fleet
    # re-registration), but the column must sync.
    second = _create_implementation(_input(idempotent=True), agent).action
    assert second.pk == first.pk
    assert second.hash == original_hash
    assert second.idempotent is True


@pytest.mark.django_db
def test_pure_with_physical_effect_is_rejected():
    agent = _agent("quali-phys")
    with pytest.raises(ValueError, match="PHYSICAL effect class"):
        _create_implementation(_input(pure=True, effect="PHYSICAL"), agent)


@pytest.mark.django_db
def test_pure_with_stateful_is_rejected():
    agent = _agent("quali-state")
    with pytest.raises(ValueError, match="pure and stateful"):
        _create_implementation(_input(pure=True, stateful=True), agent)
