"""Round-trip of port ``requires`` / ``provides`` descriptors through registration.

The bug that motivated these tests was client-side (the agent was not sending the
descriptors), but they lock in that the *server* round-trips them: ``requires`` on arg ports
and ``provides`` on return ports must survive the strawberry -> pydantic input decode, be
persisted into the Action's ``args`` / ``returns`` JSON during registration, and read back
out through the same models the ``Action.args`` / ``Action.returns`` GraphQL resolvers use.
"""

import pytest

from rekuest_core import enums as renums
from rekuest_core.inputs import types as ritypes
from rekuest_core.inputs.models import ImplementationInputModel
from rekuest_core.objects import models as rmodels

from facade import models
from facade.mutations.implementation import _create_implementation

from tests.factories import create_agent_for_registry, create_registry_bundle


def test_argport_input_to_pydantic_preserves_requires():
    """The strawberry ArgPortInput -> pydantic conversion keeps the requires descriptors.

    This is the decode the client payload goes through; a drop here is the server-side analog
    of the client bug.
    """
    port = ritypes.ArgPortInput(
        key="image",
        kind=renums.PortKind.STRUCTURE,
        identifier="@mikro/image",
        requires=[ritypes.RequiresInput(key="axes", operator=renums.RequiresOperator.EQUALS, value="c")],
    )

    model = port.to_pydantic()

    assert model.requires is not None and len(model.requires) == 1
    assert model.requires[0].key == "axes"
    assert model.requires[0].operator == renums.RequiresOperator.EQUALS
    assert model.requires[0].value == "c"


def test_returnport_input_to_pydantic_preserves_provides():
    """The strawberry ReturnPortInput -> pydantic conversion keeps the provides descriptors."""
    port = ritypes.ReturnPortInput(
        key="mask",
        kind=renums.PortKind.STRUCTURE,
        identifier="@mikro/mask",
        provides=[ritypes.ProvidesInput(key="axes", operator=renums.ProvidesOperator.EQUALS, value="c")],
    )

    model = port.to_pydantic()

    assert model.provides is not None and len(model.provides) == 1
    assert model.provides[0].key == "axes"
    assert model.provides[0].operator == renums.ProvidesOperator.EQUALS
    assert model.provides[0].value == "c"


def _implementation_input():
    return ImplementationInputModel.model_validate(
        {
            "interface": "thresholder",
            "definition": {
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
                "returns": [
                    {
                        "key": "mask",
                        "kind": "STRUCTURE",
                        "identifier": "@mikro/mask",
                        "nullable": False,
                        "provides": [{"key": "axes", "operator": "EQUALS", "value": "c"}],
                    }
                ],
            },
        }
    )


@pytest.mark.django_db
def test_create_implementation_persists_and_reads_back_descriptors():
    """Registering an implementation persists requires/provides and they survive a DB round-trip."""
    user, _, org, caller = create_registry_bundle("impl-desc")
    agent = create_agent_for_registry(caller, user, org, "impl-desc")

    implementation = _create_implementation(_implementation_input(), agent)

    # Re-read from the DB so we assert against the JSON that was actually persisted (and decoded),
    # not the in-memory pydantic dump.
    action = models.Action.objects.get(pk=implementation.action.pk)

    assert action.args[0]["requires"] == [{"key": "axes", "operator": "EQUALS", "value": "c"}]
    assert action.returns[0]["provides"] == [{"key": "axes", "operator": "EQUALS", "value": "c"}]

    # Read back through the same models the Action.args / Action.returns resolvers use
    # (facade/types/action.py) — i.e. what a GraphQL client actually receives.
    arg = rmodels.ArgPortModel(**action.args[0])
    ret = rmodels.ReturnPortModel(**action.returns[0])

    assert arg.requires[0].key == "axes" and arg.requires[0].value == "c"
    assert ret.provides[0].key == "axes" and ret.provides[0].value == "c"
