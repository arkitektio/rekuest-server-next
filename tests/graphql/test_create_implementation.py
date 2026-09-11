"""``createImplementation`` runs the same port validation as ``implementAgent``.

It used to pass the raw strawberry input where the pydantic model was expected, so none of the
port validators ran on that path (and it could not even hash the definition).
"""

import pytest
from kante.context import HttpContext

from facade.schema import schema

CREATE_IMPLEMENTATION = """
    mutation CreateImplementation($input: CreateImplementationInput!) {
        createImplementation(input: $input) {
            id
            interface
            action { name args { key kind children { key } } }
        }
    }
"""


def _input(args: list[dict]) -> dict:
    return {"input": {"implementation": {"interface": "scan", "definition": {"key": "scan", "version": "1", "name": "Scan", "kind": "FUNCTION", "args": args, "returns": []}}}}


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
class TestCreateImplementation:
    async def test_malformed_ports_are_rejected(self, authenticated_context: HttpContext) -> None:
        """A LIST port without its item child never reaches the database."""
        result = await schema.execute(CREATE_IMPLEMENTATION, context_value=authenticated_context, variable_values=_input([{"key": "xs", "kind": "LIST", "nullable": False}]))
        assert result.errors and "exactly one child" in result.errors[0].message

    async def test_valid_definition_is_registered(self, authenticated_context: HttpContext) -> None:
        """Valid definition is registered."""
        args = [{"key": "xs", "kind": "LIST", "nullable": False, "children": [{"key": "...", "kind": "STRUCTURE", "identifier": "@mikro/image", "nullable": False}]}]
        result = await schema.execute(CREATE_IMPLEMENTATION, context_value=authenticated_context, variable_values=_input(args))
        assert not result.errors, result.errors
        implementation = result.data["createImplementation"]
        assert implementation["interface"] == "scan"
        assert implementation["action"]["args"] == [{"key": "xs", "kind": "LIST", "children": [{"key": "..."}]}]
