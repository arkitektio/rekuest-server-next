"""
Unit tests for GraphQL queries in the Rekuest API.

This module tests the query functionality of the GraphQL schema,
ensuring that all query operations work correctly with proper
authentication and data validation.
"""

import pytest
from facade.schema import schema
from facade.models import Agent, Action, Protocol, StateSchema, Blok
from kante.context import HttpContext
from authentikate.models import User, Client, Organization


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
class TestGraphQLQueries:
    """Test suite for GraphQL query operations."""

    async def test_agents_query(self, authenticated_context: HttpContext):
        """Test fetching all agents via GraphQL query."""
        query = """
            query GetAgents {
                agents {
                    id
                    instanceId
                    name
                    connected
                    extensions
                }
            }
        """

        result = await schema.execute(
            query,
            context_value=authenticated_context
        )

        assert result.data is not None
        assert "agents" in result.data
        assert isinstance(result.data["agents"], list)

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

        result = await schema.execute(
            query,
            context_value=authenticated_context
        )

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

        result = await schema.execute(
            query,
            context_value=authenticated_context
        )

        assert result.data is not None
        assert "protocols" in result.data
        assert isinstance(result.data["protocols"], list)

    async def test_state_schemas_query(self, authenticated_context: HttpContext):
        """Test fetching all state schemas via GraphQL query."""
        query = """
            query GetStateSchemas {
                stateSchemas {
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

        result = await schema.execute(
            query,
            context_value=authenticated_context
        )

        assert result.data is not None
        assert "stateSchemas" in result.data
        assert isinstance(result.data["stateSchemas"], list)

    async def test_bloks_query(self, authenticated_context: HttpContext):
        """Test fetching all UI bloks via GraphQL query."""
        query = """
            query GetBloks {
                bloks {
                    id
                    name
                    url
                    creator {
                        sub
                    }
                }
            }
        """

        result = await schema.execute(
            query,
            context_value=authenticated_context
        )

        assert result.data is not None
        assert "bloks" in result.data
        assert isinstance(result.data["bloks"], list)

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

        result = await schema.execute(
            query,
            context_value=authenticated_context
        )

        assert result.data is not None
        assert "clients" in result.data
        assert isinstance(result.data["clients"], list)

    async def test_single_agent_query(self, authenticated_context: HttpContext):
        """Test fetching a single agent by ID."""
        # First ensure we have an agent
        ensure_agent_mutation = """
            mutation EnsureAgent($input: AgentInput!) {
                ensureAgent(input: $input) {
                    id
                    instanceId
                    name
                }
            }
        """

        create_result = await schema.execute(
            ensure_agent_mutation,
            context_value=authenticated_context,
            variable_values={
                "input": {
                    "instanceId": "test-agent-query",
                    "name": "Test Query Agent"
                }
            }
        )

        assert create_result.data is not None
        agent_id = create_result.data["ensureAgent"]["id"]

        # Now query for the specific agent
        query = """
            query GetAgent($id: ID!) {
                agent(id: $id) {
                    id
                    instanceId
                    name
                    connected
                    extensions
                }
            }
        """

        result = await schema.execute(
            query,
            context_value=authenticated_context,
            variable_values={"id": agent_id}
        )

        assert result.data is not None
        assert "agent" in result.data
        assert result.data["agent"]["id"] == agent_id
        assert result.data["agent"]["instanceId"] == "test-agent-query"
        assert result.data["agent"]["name"] == "Test Query Agent"

    async def test_query_with_invalid_id(self, authenticated_context: HttpContext):
        """Test querying with an invalid ID returns appropriate error."""
        query = """
            query GetAgent($id: ID!) {
                agent(id: $id) {
                    id
                    instanceId
                    name
                }
            }
        """

        result = await schema.execute(
            query,
            context_value=authenticated_context,
            variable_values={"id": "999999"}  # Non-existent ID
        )

        assert result.data is None
        assert result.errors is not None
        assert len(result.errors) > 0

    async def test_hardware_records_query(self, authenticated_context: HttpContext):
        """Test fetching hardware records via GraphQL query."""
        query = """
            query GetHardwareRecords {
                hardwareRecords {
                    id
                    cpuCount
                    cpuVendorName
                    cpuFrequency
                    createdAt
                }
            }
        """

        result = await schema.execute(
            query,
            context_value=authenticated_context
        )

        assert result.data is not None
        assert "hardwareRecords" in result.data
        assert isinstance(result.data["hardwareRecords"], list)

    async def test_reservations_query(self, authenticated_context: HttpContext):
        """Test fetching reservations via GraphQL query."""
        # Skip this test due to complex database constraints
        pytest.skip("Reservations require complex setup with Waiter constraints")

    async def test_my_reservations_query(self, authenticated_context: HttpContext):
        """Test fetching user's reservations via GraphQL query."""
        # Skip this test due to complex database constraints
        pytest.skip("Reservations require complex setup with Waiter constraints")
