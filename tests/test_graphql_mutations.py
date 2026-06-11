"""
Unit tests for GraphQL mutations in the Rekuest API.

This module tests the mutation functionality of the GraphQL schema,
ensuring that all write operations work correctly with proper
authentication, validation, and data persistence.
"""

import pytest
from asgiref.sync import sync_to_async
from facade.schema import schema
from facade.models import Agent, Blok, Dashboard, StateDefinition
from kante.context import HttpContext


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
class TestGraphQLMutations:
    """Test suite for GraphQL mutation operations."""

    async def test_ensure_agent_mutation_with_name(self, authenticated_context: HttpContext):
        """Test creating an agent with custom name via ensureAgent mutation."""
        mutation = """
            mutation EnsureAgent($input: AgentInput!) {
                ensureAgent(input: $input) {
                    id
                    instanceId
                    name
                    connected
                }
            }
        """

        result = await schema.execute(mutation, context_value=authenticated_context, variable_values={"input": {"instanceId": "custom-test-agent", "name": "Custom Test Agent"}})

        assert result.data is not None, f"Errors: {result.errors}"
        assert "ensureAgent" in result.data

        agent = result.data["ensureAgent"]
        assert agent["instanceId"] == "custom-test-agent"
        assert agent["name"] == "Custom Test Agent"

    async def test_ensure_agent_mutation_default_name(self, authenticated_context: HttpContext):
        """Test creating an agent with default name generation."""
        mutation = """
            mutation EnsureAgent($input: AgentInput!) {
                ensureAgent(input: $input) {
                    id
                    instanceId
                    name
                }
            }
        """

        result = await schema.execute(mutation, context_value=authenticated_context, variable_values={"input": {"instanceId": "default-name-agent"}})

        assert result.data is not None, f"Errors: {result.errors}"
        assert "ensureAgent" in result.data

        agent = result.data["ensureAgent"]
        assert agent["instanceId"] == "default-name-agent"
        assert agent["name"] is not None  # Should have auto-generated name

    async def test_ensure_agent_mutation_duplicate_instance_id(self, authenticated_context: HttpContext):
        """Test that ensuring agent with the same instanceId reuses the existing record."""
        mutation = """
            mutation EnsureAgent($input: AgentInput!) {
                ensureAgent(input: $input) {
                    id
                    instanceId
                    name
                    extensions
                }
            }
        """

        # Create first agent
        result1 = await schema.execute(mutation, context_value=authenticated_context, variable_values={"input": {"instanceId": "duplicate-test", "name": "First Agent"}})

        assert result1.data is not None
        first_agent_id = result1.data["ensureAgent"]["id"]

        # Ensure the same agent again with a different name hint.
        result2 = await schema.execute(mutation, context_value=authenticated_context, variable_values={"input": {"instanceId": "duplicate-test", "name": "Updated Agent"}})

        assert result2.data is not None
        second_agent_id = result2.data["ensureAgent"]["id"]

        # ensureAgent is idempotent and returns the existing record.
        assert first_agent_id == second_agent_id
        assert result2.data["ensureAgent"]["name"] == "First Agent"
        assert result2.data["ensureAgent"]["extensions"] == []
        assert await sync_to_async(lambda: Agent.objects.filter(instance_id="duplicate-test").count())() == 1

    async def test_state_definitions_query(self, authenticated_context: HttpContext):
        """Test that seeded state definitions are exposed via GraphQL."""
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

    async def test_create_blok_mutation(self, authenticated_context: HttpContext):
        """Test creating a UI blok via mutation."""
        mutation = """
            mutation CreateBlok($input: CreateBlokInput!) {
                createBlok(input: $input) {
                    id
                    name
                    description
                    creator {
                        sub
                    }
                }
            }
        """

        result = await schema.execute(mutation, context_value=authenticated_context, variable_values={"input": {"name": "Test UI Blok", "uri": "http://example.com/blok", "description": "A test UI component", "demoState": {}}})

        assert result.data is not None, f"Errors: {result.errors}"
        assert "createBlok" in result.data

        blok = result.data["createBlok"]
        assert blok["name"] == "Test UI Blok"
        assert blok["description"] == "A test UI component"

    async def test_create_dashboard_mutation(self, authenticated_context: HttpContext):
        """Test creating a dashboard via mutation."""
        mutation = """
            mutation CreateDashboard($input: CreateDashboardInput!) {
                createDashboard(input: $input) {
                    id
                    name
                }
            }
        """

        result = await schema.execute(mutation, context_value=authenticated_context, variable_values={"input": {"name": "Test Dashboard"}})

        assert result.data is not None, f"Errors: {result.errors}"
        assert "createDashboard" in result.data

        dashboard = result.data["createDashboard"]
        assert dashboard["name"] == "Test Dashboard"

    async def test_delete_agent_mutation(self, authenticated_context: HttpContext):
        """Test deleting an agent via mutation."""
        # First create an agent
        ensure_mutation = """
            mutation EnsureAgent($input: AgentInput!) {
                ensureAgent(input: $input) {
                    id
                    instanceId
                }
            }
        """

        create_result = await schema.execute(ensure_mutation, context_value=authenticated_context, variable_values={"input": {"instanceId": "agent-to-delete", "name": "Agent To Delete"}})

        assert create_result.data is not None
        agent_id = create_result.data["ensureAgent"]["id"]

        # Now delete the agent
        delete_mutation = """
            mutation DeleteAgent($input: DeleteAgentInput!) {
                deleteAgent(input: $input)
            }
        """

        delete_result = await schema.execute(delete_mutation, context_value=authenticated_context, variable_values={"input": {"id": agent_id}})

        assert delete_result.data is not None
        assert delete_result.data["deleteAgent"] == agent_id

        # Verify agent is deleted by trying to query it
        query = """
            query GetAgent($id: ID!) {
                agent(id: $id) {
                    id
                }
            }
        """

        query_result = await schema.execute(query, context_value=authenticated_context, variable_values={"id": agent_id})

        assert query_result.data is None
        assert query_result.errors is not None

    async def test_mutation_without_authentication(self):
        """Test that mutations require authentication."""
        mutation = """
            mutation EnsureAgent($input: AgentInput!) {
                ensureAgent(input: $input) {
                    id
                    instanceId
                }
            }
        """

        # Create a context without authentication
        from kante.context import HttpContext, UniversalRequest

        unauthenticated_context = HttpContext(
            request=UniversalRequest(
                _extensions={},
                _client=None,
                _user=None,
                _organization=None,
            ),
            headers={},
            type="http",
        )

        result = await schema.execute(mutation, context_value=unauthenticated_context, variable_values={"input": {"instanceId": "unauthorized-agent"}})

        # Should fail due to lack of authentication
        assert result.data is None or result.errors is not None

    async def test_invalid_input_mutation(self, authenticated_context: HttpContext):
        """Test mutation with invalid input data."""
        mutation = """
            mutation EnsureAgent($input: AgentInput!) {
                ensureAgent(input: $input) {
                    id
                    instanceId
                }
            }
        """

        result = await schema.execute(
            mutation,
            context_value=authenticated_context,
            variable_values={
                "input": {
                    # Missing required instanceId field
                    "name": "Invalid Agent"
                }
            },
        )

        # Should fail due to missing required field
        assert result.errors is not None
