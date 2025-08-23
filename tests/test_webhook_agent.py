"""Test webhook agent functionality."""

import pytest
from facade.mutations.agent import AgentInput, ensure_agent
from facade import models, enums


@pytest.mark.django_db(transaction=True)  
@pytest.mark.asyncio
class TestWebhookAgent:
    """Test suite for webhook agent functionality."""

    async def test_ensure_webhook_agent_with_valid_data(self, authenticated_context):
        """Test creating a webhook agent with valid webhook data."""
        agent_input = AgentInput(
            instance_id="webhook-test",
            name="Test Webhook Agent",
            extensions=["test_ext"],
            kind="WEBHOOK",
            hook_url="https://example.com/webhook",
            hook_url_secret="secret123"
        )

        agent = await ensure_agent(authenticated_context, agent_input)

        assert agent is not None
        assert agent.instance_id == "webhook-test"
        assert agent.name == "Test Webhook Agent"
        assert agent.kind == enums.AgentKind.WEBHOOK.value
        assert agent.hook_url == "https://example.com/webhook"
        assert agent.hook_url_secret == "secret123"