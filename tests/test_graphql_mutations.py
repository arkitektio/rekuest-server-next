"""
Unit tests for GraphQL mutations in the Rekuest API.

This module tests the mutation functionality of the GraphQL schema,
ensuring that all write operations work correctly with proper
authentication, validation, and data persistence.
"""

import pytest
from facade.schema import schema
from facade.models import Agent, Blok, Dashboard
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
                    extensions
                    connected
                }
            }
        """

        result = await schema.execute(mutation, context_value=authenticated_context, variable_values={"input": {"instanceId": "custom-test-agent", "name": "Custom Test Agent", "extensions": ["test-extension-1", "test-extension-2"]}})

        assert result.data is not None, f"Errors: {result.errors}"
        assert "ensureAgent" in result.data

        agent = result.data["ensureAgent"]
        assert agent["instanceId"] == "custom-test-agent"
        assert agent["name"] == "Custom Test Agent"
        assert agent["extensions"] == ["test-extension-1", "test-extension-2"]

    async def test_ensure_agent_mutation_default_name(self, authenticated_context: HttpContext):
        """Test creating an agent with default name generation."""
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

        result = await schema.execute(mutation, context_value=authenticated_context, variable_values={"input": {"instanceId": "default-name-agent"}})

        assert result.data is not None, f"Errors: {result.errors}"
        assert "ensureAgent" in result.data

        agent = result.data["ensureAgent"]
        assert agent["instanceId"] == "default-name-agent"
        assert agent["name"] is not None  # Should have auto-generated name
        assert agent["extensions"] == []  # Should default to empty list

    async def test_ensure_agent_mutation_duplicate_instance_id(self, authenticated_context: HttpContext):
        """Test that ensuring agent with same instanceId updates existing record."""
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
        result1 = await schema.execute(mutation, context_value=authenticated_context, variable_values={"input": {"instanceId": "duplicate-test", "name": "First Agent", "extensions": ["ext1"]}})

        assert result1.data is not None
        first_agent_id = result1.data["ensureAgent"]["id"]

        # Create second agent with same instanceId but different name
        result2 = await schema.execute(mutation, context_value=authenticated_context, variable_values={"input": {"instanceId": "duplicate-test", "name": "Updated Agent", "extensions": ["ext2"]}})

        assert result2.data is not None
        second_agent_id = result2.data["ensureAgent"]["id"]

        # Should be the same agent (updated, not created)
        assert first_agent_id == second_agent_id
        assert result2.data["ensureAgent"]["name"] == "Updated Agent"
        assert result2.data["ensureAgent"]["extensions"] == ["ext2"]

    async def test_create_state_schema_mutation(self, authenticated_context: HttpContext):
        """Test creating a state schema via mutation."""
        mutation = """
            mutation CreateStateSchema($input: CreateStateSchemaInput!) {
                createStateSchema(input: $input) {
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

        state_schema_input = {"name": "Test State Schema", "ports": [{"key": "input_port", "kind": "STRING", "identifier": "test.input", "description": "Test input port"}, {"key": "output_port", "kind": "INT", "identifier": "test.output", "description": "Test output port"}]}

        result = await schema.execute(mutation, context_value=authenticated_context, variable_values={"input": {"stateSchema": state_schema_input}})

        assert result.data is not None, f"Errors: {result.errors}"
        assert "createStateSchema" in result.data

        schema_data = result.data["createStateSchema"]
        assert schema_data["name"] == "Test State Schema"
        assert len(schema_data["ports"]) == 2
        assert schema_data["hash"] is not None

    async def test_create_blok_mutation(self, authenticated_context: HttpContext):
        """Test creating a UI blok via mutation."""
        mutation = """
            mutation CreateBlok($input: CreateBlokInput!) {
                createBlok(input: $input) {
                    id
                    name
                    description
                    url
                    creator {
                        sub
                    }
                }
            }
        """

        result = await schema.execute(mutation, context_value=authenticated_context, variable_values={"input": {"name": "Test UI Blok", "url": "http://example.com/blok", "actionDemands": [], "description": "A test UI component", "stateDemands": []}})

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
