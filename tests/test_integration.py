"""
Integration tests for the Rekuest API.

This module contains end-to-end tests that verify the complete
workflow of agent registration, task execution, and state management.
"""

import pytest
from facade.schema import schema
from facade.models import Agent, Action
from kante.context import HttpContext
import asyncio


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
class TestIntegration:
    """Integration test suite for complete workflows."""

    async def test_agent_lifecycle_workflow(self, authenticated_context: HttpContext):
        """Test complete agent lifecycle from registration to deletion."""

        # Step 1: Register agent
        ensure_agent_mutation = """
            mutation EnsureAgent($input: AgentInput!) {
                ensureAgent(input: $input) {
                    id
                    instanceId
                    name
                    connected
                }
            }
        """

        agent_result = await schema.execute(ensure_agent_mutation, context_value=authenticated_context, variable_values={"input": {"instanceId": "integration-test-agent", "name": "Integration Test Agent"}})

        assert agent_result.data is not None
        agent_id = agent_result.data["ensureAgent"]["id"]
        assert agent_result.data["ensureAgent"]["instanceId"] == "integration-test-agent"

        # Step 2: Query for the agent
        agent_query = """
            query GetAgent($id: ID!) {
                agent(id: $id) {
                    id
                    instanceId
                    name
                }
            }
        """

        query_result = await schema.execute(agent_query, context_value=authenticated_context, variable_values={"id": agent_id})

        assert query_result.data is not None
        assert query_result.data["agent"]["instanceId"] == "integration-test-agent"

        # Step 3: Ensuring the same agent again should be idempotent.
        update_result = await schema.execute(ensure_agent_mutation, context_value=authenticated_context, variable_values={"input": {"instanceId": "integration-test-agent", "name": "Updated Integration Agent"}})

        assert update_result.data is not None
        assert update_result.data["ensureAgent"]["id"] == agent_id  # Same agent
        assert update_result.data["ensureAgent"]["name"] == "Integration Test Agent"

        # Step 4: Delete the agent
        delete_mutation = """
            mutation DeleteAgent($input: DeleteAgentInput!) {
                deleteAgent(input: $input)
            }
        """

        delete_result = await schema.execute(delete_mutation, context_value=authenticated_context, variable_values={"input": {"id": agent_id}})

        assert delete_result.data is not None
        assert delete_result.data["deleteAgent"] == agent_id

        # Step 5: Verify agent is deleted
        final_query_result = await schema.execute(agent_query, context_value=authenticated_context, variable_values={"id": agent_id})

        assert final_query_result.data is None
        assert final_query_result.errors is not None

    async def test_multiple_agents_workflow(self, authenticated_context: HttpContext):
        """Test managing multiple agents simultaneously."""

        agent_ids = []

        # Step 1: Create multiple agents
        ensure_agent_mutation = """
            mutation EnsureAgent($input: AgentInput!) {
                ensureAgent(input: $input) {
                    id
                    instanceId
                    name
                }
            }
        """

        for i in range(3):
            result = await schema.execute(ensure_agent_mutation, context_value=authenticated_context, variable_values={"input": {"instanceId": f"multi-agent-{i}", "name": f"Multi Agent {i}"}})

            assert result.data is not None
            agent_ids.append(result.data["ensureAgent"]["id"])

        # Step 2: Query all agents
        agents_query = """
            query GetAgents {
                agents {
                    id
                    instanceId
                    name
                }
            }
        """

        all_agents_result = await schema.execute(agents_query, context_value=authenticated_context)

        assert all_agents_result.data is not None
        agents = all_agents_result.data["agents"]

        # Check that our test agents are in the results
        agent_instance_ids = [agent["instanceId"] for agent in agents]
        for i in range(3):
            assert f"multi-agent-{i}" in agent_instance_ids

        # Step 3: Delete all test agents
        delete_mutation = """
            mutation DeleteAgent($input: DeleteAgentInput!) {
                deleteAgent(input: $input)
            }
        """

        for agent_id in agent_ids:
            delete_result = await schema.execute(delete_mutation, context_value=authenticated_context, variable_values={"input": {"id": agent_id}})
            assert delete_result.data is not None

    async def test_dashboard_and_blok_workflow(self, authenticated_context: HttpContext):
        """Test creating UI components workflow."""

        # Step 1: Create a blok
        create_blok_mutation = """
            mutation CreateBlok($input: CreateBlokInput!) {
                createBlok(input: $input) {
                    id
                    name
                    creator {
                        sub
                    }
                }
            }
        """

        blok_result = await schema.execute(create_blok_mutation, context_value=authenticated_context, variable_values={"input": {"name": "Integration Test Blok", "demoState": {}}})

        assert blok_result.data is not None
        blok_id = blok_result.data["createBlok"]["id"]

        # Step 2: Create a dashboard
        create_dashboard_mutation = """
            mutation CreateDashboard($input: CreateDashboardInput!) {
                createDashboard(input: $input) {
                    id
                    name
                }
            }
        """

        dashboard_result = await schema.execute(create_dashboard_mutation, context_value=authenticated_context, variable_values={"input": {"name": "Integration Test Dashboard"}})

        assert dashboard_result.data is not None
        dashboard_id = dashboard_result.data["createDashboard"]["id"]

        # Step 3: Query for created resources
        dashboard_query = """
            query GetDashboard($id: ID!) {
                dashboard(id: $id) {
                    id
                    name
                }
            }
        """

        dashboard_query_result = await schema.execute(dashboard_query, context_value=authenticated_context, variable_values={"id": dashboard_id})

        assert dashboard_query_result.data is not None
        assert dashboard_query_result.data["dashboard"]["name"] == "Integration Test Dashboard"

        blok_query = """
            query GetBlok($id: ID!) {
                blok(id: $id) {
                    id
                    name
                    description
                }
            }
        """

        blok_query_result = await schema.execute(blok_query, context_value=authenticated_context, variable_values={"id": blok_id})

        assert blok_query_result.data is not None
        assert blok_query_result.data["blok"]["name"] == "Integration Test Blok"

    async def test_error_handling_workflow(self, authenticated_context: HttpContext):
        """Test proper error handling in various scenarios."""

        # Test 1: Query non-existent agent
        agent_query = """
            query GetAgent($id: ID!) {
                agent(id: $id) {
                    id
                    name
                }
            }
        """

        error_result = await schema.execute(agent_query, context_value=authenticated_context, variable_values={"id": "999999"})

        assert error_result.data is None
        assert error_result.errors is not None

        # Test 2: Create agent with invalid data
        ensure_agent_mutation = """
            mutation EnsureAgent($input: AgentInput!) {
                ensureAgent(input: $input) {
                    id
                    instanceId
                }
            }
        """

        invalid_result = await schema.execute(
            ensure_agent_mutation,
            context_value=authenticated_context,
            variable_values={
                "input": {
                    # Missing required instanceId
                    "name": "Invalid Agent"
                }
            },
        )

        assert invalid_result.errors is not None

        # Test 3: Delete non-existent agent
        delete_mutation = """
            mutation DeleteAgent($input: DeleteAgentInput!) {
                deleteAgent(input: $input)
            }
        """

        delete_error_result = await schema.execute(delete_mutation, context_value=authenticated_context, variable_values={"input": {"id": "999999"}})

        assert delete_error_result.errors is not None
