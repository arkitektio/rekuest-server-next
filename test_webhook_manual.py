#!/usr/bin/env python3
"""Manual test script for webhook agent functionality."""

import os
import django
import asyncio
from pathlib import Path

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rekuest.settings_test')

# Add the project root to Python path
import sys
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

django.setup()

# Run migrations for the test database 
from django.core.management import execute_from_command_line
execute_from_command_line(['manage.py', 'migrate', '--run-syncdb'])

# Now we can import our Django models and functions
from facade.mutations.agent import AgentInput, ensure_agent
from facade import models, enums
from authentikate.models import Client, Organization, User
from kante.context import HttpContext, UniversalRequest


async def test_webhook_agent():
    """Test webhook agent creation."""
    
    # Create test user, client, and organization
    user = await User.objects.acreate(username="testuser", password="testpass", sub="test_sub")
    client = await Client.objects.acreate(client_id="testclient")
    org = await Organization.objects.acreate(slug="test-org")
    
    # Create context
    context = HttpContext(
        request=UniversalRequest(
            _extensions={"token": "token"},
            _client=client,
            _user=user,
            _organization=org,
        ),
        headers={"Authorization": "Bearer token"},
        type="http"
    )
    
    # Test webhook agent creation
    agent_input = AgentInput(
        instance_id="webhook-test",
        name="Test Webhook Agent",
        extensions=["test_ext"],
        kind="WEBHOOK",
        hook_url="https://example.com/webhook",
        hook_url_secret="secret123"
    )
    
    agent = await ensure_agent(context, agent_input)
    
    print(f"Created agent: {agent.id}")
    print(f"Agent name: {agent.name}")
    print(f"Agent kind: {agent.kind}")
    print(f"Agent hook_url: {agent.hook_url}")
    print(f"Agent hook_url_secret: {agent.hook_url_secret}")
    
    # Verify the agent was saved correctly
    assert agent.kind == enums.AgentKind.WEBHOOK.value
    assert agent.hook_url == "https://example.com/webhook"
    assert agent.hook_url_secret == "secret123"
    
    print("✅ Webhook agent test passed!")
    
    # Test websocket agent (default)
    ws_agent_input = AgentInput(
        instance_id="websocket-test",
        name="Test WebSocket Agent",
        extensions=["test_ext"]
    )
    
    ws_agent = await ensure_agent(context, ws_agent_input)
    
    print(f"Created WebSocket agent: {ws_agent.id}")
    print(f"Agent kind: {ws_agent.kind}")
    
    assert ws_agent.kind == enums.AgentKind.WEBSOCKET.value
    assert ws_agent.hook_url is None
    assert ws_agent.hook_url_secret is None
    
    print("✅ WebSocket agent test passed!")
    
    # Test validation error
    try:
        invalid_agent_input = AgentInput(
            instance_id="invalid-test",
            name="Test Invalid Agent",
            kind="WEBHOOK",
            hook_url="https://example.com/webhook"
            # Missing hook_url_secret
        )
        await ensure_agent(context, invalid_agent_input)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"✅ Validation test passed: {e}")


if __name__ == "__main__":
    asyncio.run(test_webhook_agent())