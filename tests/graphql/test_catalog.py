"""GraphQL catalog queries: actions, protocols, state schemas and clients."""

import pytest
from asgiref.sync import sync_to_async
from kante.context import HttpContext

from facade.models import StateDefinition
from facade.schema import schema


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
class TestGraphQLCatalog:
    """Read-side GraphQL operations over the action/protocol/state catalog."""

    async def test_actions_query(self, authenticated_context: HttpContext):
        """Test fetching all actions via GraphQL query."""
        query = """
            query GetActions {
                actions {
                    id
                    name
                    description
                    hash
                }
            }
        """

        result = await schema.execute(query, context_value=authenticated_context)

        assert result.data is not None
        assert "actions" in result.data
        assert isinstance(result.data["actions"], list)

    async def test_protocols_query(self, authenticated_context: HttpContext):
        """Test fetching all protocols via GraphQL query."""
        query = """
            query GetProtocols {
                protocols {
                    id
                    name
                    actions {
                        id
                        name
                    }
                }
            }
        """

        result = await schema.execute(query, context_value=authenticated_context)

        assert result.data is not None
        assert "protocols" in result.data
        assert isinstance(result.data["protocols"], list)

    async def test_state_schemas_query(self, authenticated_context: HttpContext):
        """Test fetching all state definitions via GraphQL query."""
        await sync_to_async(StateDefinition.objects.create)(
            name="Query State Definition",
            hash="query-state-definition-hash",
            description="State definition for query testing",
            ports=[{"key": "output", "kind": "STRING", "identifier": "test.output", "nullable": False, "effects": [], "children": []}],
        )

        query = """
            query GetStateDefinitions {
                stateDefinitions {
                    id
                    name
                    hash
                    ports {
                        key
                        kind
                        identifier
                        nullable
                    }
                }
            }
        """

        result = await schema.execute(query, context_value=authenticated_context)

        assert result.data is not None
        assert "stateDefinitions" in result.data
        assert isinstance(result.data["stateDefinitions"], list)
        assert any(item["hash"] == "query-state-definition-hash" for item in result.data["stateDefinitions"])

    async def test_state_definitions_with_ports(self, authenticated_context: HttpContext):
        """Test that a seeded state definition with ports is exposed via GraphQL."""
        await sync_to_async(StateDefinition.objects.create)(
            name="Test State Schema",
            hash="state-hash-graphql",
            description="A test state schema",
            ports=[
                {"key": "input_port", "kind": "STRING", "identifier": "test.input", "nullable": False, "effects": [], "children": []},
                {"key": "output_port", "kind": "INT", "identifier": "test.output", "nullable": False, "effects": [], "children": []},
            ],
        )

        query = """
            query GetStateDefinitions {
                stateDefinitions {
                    id
                    name
                    hash
                    ports {
                        key
                        kind
                        identifier
                        nullable
                    }
                }
            }
        """

        result = await schema.execute(query, context_value=authenticated_context)

        assert result.data is not None, f"Errors: {result.errors}"
        assert "stateDefinitions" in result.data

        matching_definitions = [item for item in result.data["stateDefinitions"] if item["hash"] == "state-hash-graphql"]
        assert len(matching_definitions) == 1
        schema_data = matching_definitions[0]
        assert schema_data["name"] == "Test State Schema"
        assert len(schema_data["ports"]) == 2

    async def test_clients_query(self, authenticated_context: HttpContext):
        """Test fetching all clients via GraphQL query."""
        query = """
            query GetClients {
                clients {
                    id
                    clientId
                }
            }
        """

        result = await schema.execute(query, context_value=authenticated_context)

        assert result.data is not None
        assert "clients" in result.data
        assert isinstance(result.data["clients"], list)
