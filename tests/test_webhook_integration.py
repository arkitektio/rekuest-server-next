"""Integration tests for webhook agent functionality."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import json
import httpx

from facade.mutations.agent import AgentInput, ensure_agent
from facade.webhook_service import webhook_service
from facade import models, enums, messages
from django.test import RequestFactory
from facade.views import WebhookAgentEventView


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio  
class TestWebhookAgentIntegration:
    """Integration tests for webhook agent functionality."""

    async def test_webhook_agent_lifecycle(self, authenticated_context):
        """Test complete webhook agent lifecycle from registration to event handling."""
        
        # 1. Register webhook agent
        agent_input = AgentInput(
            instance_id="integration-webhook-test",
            name="Integration Test Webhook Agent",
            extensions=["test_integration"],
            kind="WEBHOOK", 
            hook_url="https://webhook-server.example.com/tasks",
            hook_url_secret="integration-test-secret-123"
        )

        agent = await ensure_agent(authenticated_context, agent_input)
        
        # Verify webhook agent was created correctly
        assert agent.kind == enums.AgentKind.WEBHOOK.value
        assert agent.hook_url == "https://webhook-server.example.com/tasks"
        assert agent.hook_url_secret == "integration-test-secret-123"

    @patch('facade.webhook_service.httpx.AsyncClient.post')
    async def test_webhook_message_sending(self, mock_post):
        """Test webhook service sends messages correctly."""
        
        # Mock successful HTTP response
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        # Create test agent
        agent = models.Agent(
            id=123,
            hook_url="https://test.example.com/webhook", 
            hook_url_secret="test-secret"
        )
        
        # Create test message
        assign_message = messages.Assign(
            assignation="test-assignation-123",
            args={"param1": "value1"},
            user="user123", 
            app="app123",
            interface="test.interface",
            extension="test.ext",
            action="action-hash-123"
        )
        
        # Send message via webhook service
        result = await webhook_service.send_message_to_webhook_agent(agent, assign_message)
        
        # Verify message was sent correctly  
        assert result is True
        mock_post.assert_called_once()
        
        # Verify call parameters
        call_args = mock_post.call_args
        assert call_args[1]['url'] == "https://test.example.com/webhook"
        assert call_args[1]['headers']['Content-Type'] == "application/json"
        assert call_args[1]['headers']['Authorization'] == "Bearer test-secret"
        assert call_args[1]['headers']['X-Agent-Secret'] == "test-secret"
        
        # Verify payload structure
        payload = call_args[1]['json']
        assert payload['agent_id'] == "123"
        assert payload['message']['assignation'] == "test-assignation-123"
        assert payload['message']['type'] == "ASSIGN"

    async def test_webhook_event_view(self):
        """Test webhook event endpoint handles requests correctly."""
        
        # Create test agent
        agent = await models.Agent.objects.acreate(
            name="Test Webhook Agent",
            kind=enums.AgentKind.WEBHOOK.value,
            hook_url="https://test.example.com/webhook",
            hook_url_secret="view-test-secret"
        )
        
        # Create test request data
        request_data = {
            "agent_id": str(agent.id),
            "message": {
                "type": "PROGRESS",
                "assignation": "test-assignation-456", 
                "progress": 50,
                "message": "Halfway complete"
            }
        }
        
        # Create Django request
        factory = RequestFactory()
        request = factory.post(
            '/webhook/agent/events/',
            data=json.dumps(request_data),
            content_type='application/json',
            HTTP_AUTHORIZATION='Bearer view-test-secret'
        )
        
        # Mock persist_backend to avoid database complexity
        with patch('facade.views.persist_backend') as mock_persist:
            mock_persist.on_agent_progress = AsyncMock()
            
            # Process request through view
            view = WebhookAgentEventView()
            response = await view.post(request)
            
            # Verify response
            assert response.status_code == 200
            response_data = json.loads(response.content.decode())
            assert response_data['status'] == 'success'
            
            # Verify persist_backend was called
            mock_persist.on_agent_progress.assert_called_once()

    async def test_invalid_webhook_secret(self):
        """Test that invalid webhook secret is rejected."""
        
        # Create test agent
        agent = await models.Agent.objects.acreate(
            name="Test Webhook Agent",
            kind=enums.AgentKind.WEBHOOK.value,
            hook_url="https://test.example.com/webhook",
            hook_url_secret="correct-secret"
        )
        
        # Create request with wrong secret
        request_data = {
            "agent_id": str(agent.id), 
            "message": {
                "type": "PROGRESS",
                "assignation": "test-assignation-789",
                "progress": 25
            }
        }
        
        factory = RequestFactory()
        request = factory.post(
            '/webhook/agent/events/',
            data=json.dumps(request_data),
            content_type='application/json',
            HTTP_AUTHORIZATION='Bearer wrong-secret'  # Wrong secret
        )
        
        # Process request
        view = WebhookAgentEventView()
        response = await view.post(request)
        
        # Verify rejection
        assert response.status_code == 401
        response_data = json.loads(response.content.decode())
        assert 'Invalid secret' in response_data['error']