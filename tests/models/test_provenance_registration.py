"""Audience is resolved at implementation registration, from the action's ports.

Drives the real ``_create_implementation`` path: an implementation that declares
no audience gets one derived from its arg/return structure identifiers, while an
explicit declaration is persisted verbatim. Both are stored on the model so
dispatch never recomputes them.
"""

import pytest

from rekuest_core.inputs.models import DefinitionInputModel, ImplementationInputModel

from facade.mutations.implementation import _create_implementation

from tests.factories import create_agent_for_registry, create_registry_bundle


def _definition():
    return DefinitionInputModel.model_validate(
        {
            "key": "thresholder",
            "version": "1",
            "name": "Thresholder",
            "kind": "FUNCTION",
            "args": [{"key": "image", "kind": "STRUCTURE", "identifier": "@mikro/image", "nullable": False}],
            "returns": [{"key": "mask", "kind": "STRUCTURE", "identifier": "@fluss/flow", "nullable": False}],
        }
    )


def _agent(prefix):
    user, _client, org, caller = create_registry_bundle(prefix)
    return create_agent_for_registry(caller, user, org, prefix)


@pytest.mark.django_db
def test_audience_derived_from_action_ports_at_registration():
    agent = _agent("prov-reg-derive")
    impl = _create_implementation(
        ImplementationInputModel(definition=_definition(), interface="thresholder"),
        agent,
    )
    # Derived from the arg (@mikro) + return (@fluss) structure ports.
    assert impl.provenance_audience == ["mikro", "fluss"]


@pytest.mark.django_db
def test_declared_audience_is_persisted_verbatim():
    agent = _agent("prov-reg-declared")
    impl = _create_implementation(
        ImplementationInputModel(
            definition=_definition(),
            interface="thresholder",
            provenance_audience=["explicit-service"],
        ),
        agent,
    )
    assert impl.provenance_audience == ["explicit-service"]
