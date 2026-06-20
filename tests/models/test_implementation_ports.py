"""End-to-end checks of the port write path feeding the relational matcher.

Builds an Action's relational ArgPort/ReturnPort rows through the real ``rebuild_relational_ports``
path (from a genuine ``DefinitionInputModel``) and verifies that (a) the rows + compiled requires
are created, (b) re-running rebuilds rather than duplicates the rows (the stale-rows fix), and
(c) the matching layer then finds the action by its requires micro-constraint.
"""

from types import SimpleNamespace

import pytest

from rekuest_core.inputs.models import DefinitionInputModel

from facade import managers, models
from facade.mutations.implementation import rebuild_relational_ports

from tests.factories import create_action_for_organization, create_registry_bundle


def _definition():
    return DefinitionInputModel.model_validate(
        {
            "key": "thresholder",
            "version": "1",
            "name": "Thresholder",
            "kind": "FUNCTION",
            "args": [
                {
                    "key": "image",
                    "kind": "STRUCTURE",
                    "identifier": "@mikro/image",
                    "nullable": False,
                    "requires": [{"key": "axes", "operator": "EQUALS", "value": "c"}],
                }
            ],
            "returns": [{"key": "mask", "kind": "STRUCTURE", "identifier": "@mikro/mask", "nullable": False}],
        }
    )


def _arg_object_demand(identifier, obj):
    """An ActionDemandInput-shaped object asserting a single arg's runtime descriptors."""
    descriptors = [SimpleNamespace(key=k, value=v) for k, v in obj.items()]
    match = SimpleNamespace(at=None, key=None, kind=None, identifier=identifier, descriptors=descriptors, nullable=None, children=None)
    return SimpleNamespace(
        hash=None, name=None, force_arg_length=None, force_return_length=None,
        arg_matches=[match], return_matches=None,
    )


@pytest.mark.django_db
def test_rebuild_builds_relational_ports_and_matches():
    _, _, org, _ = create_registry_bundle("impl-ports")
    action = create_action_for_organization(org, "impl-ports")

    rebuild_relational_ports(action, _definition())

    # Relational rows were built, with the compiled requires constraint on the arg port.
    assert action.arg_count == 1
    assert action.return_count == 1
    arg = action.arg_ports.get(parent__isnull=True)
    assert arg.identifier == "@mikro/image"
    assert arg.compiled_jsonpath == '$.axes == "c"'

    # The matcher finds the action by a satisfying descriptor and rejects a violating one.
    matching = managers.get_action_ids_by_action_demand(
        _arg_object_demand("@mikro/image", {"axes": "c"}), organization_id=org.id
    )
    assert action.id in matching

    rejecting = managers.get_action_ids_by_action_demand(
        _arg_object_demand("@mikro/image", {"axes": "z"}), organization_id=org.id
    )
    assert action.id not in rejecting


@pytest.mark.django_db
def test_rebuild_does_not_duplicate_ports():
    _, _, org, _ = create_registry_bundle("impl-rereg")
    action = create_action_for_organization(org, "impl-rereg")

    rebuild_relational_ports(action, _definition())
    assert models.ArgPort.objects.filter(action_id=action.id).count() == 1
    assert models.ReturnPort.objects.filter(action_id=action.id).count() == 1

    # Re-running (as on agent re-registration) must rebuild, not accumulate.
    rebuild_relational_ports(action, _definition())
    assert models.ArgPort.objects.filter(action_id=action.id).count() == 1
    assert models.ReturnPort.objects.filter(action_id=action.id).count() == 1

    refreshed = models.Action.objects.get(id=action.id)
    assert refreshed.arg_count == 1
    assert refreshed.return_count == 1
