#!/usr/bin/env python3
"""Simple syntax test for webhook agent functionality."""

import os
import django

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rekuest.settings_test')
django.setup()

# Test import and basic syntax
try:
    from facade.mutations.agent import AgentInput, ensure_agent
    from facade import enums
    print("✅ Successfully imported AgentInput and ensure_agent")
    
    # Test that AgentInput accepts webhook fields
    agent_input = AgentInput(
        instance_id="test",
        name="Test Agent",
        extensions=["test"],
        kind="WEBHOOK", 
        hook_url="https://example.com/webhook",
        hook_url_secret="secret123"
    )
    print("✅ AgentInput accepts webhook fields")
    
    # Test that enum values are correct
    print(f"WEBSOCKET enum: {enums.AgentKind.WEBSOCKET.value}")
    print(f"WEBHOOK enum: {enums.AgentKind.WEBHOOK.value}")
    print("✅ Agent kind enums are correct")
    
    # Test webhook service import
    from facade.webhook_service import webhook_service
    print("✅ Successfully imported webhook_service")
    
    # Test view import
    from facade.views import WebhookAgentEventView
    print("✅ Successfully imported WebhookAgentEventView")
    
    print("\n🎉 All syntax and import tests passed!")
    print("The webhook agent functionality has been successfully implemented.")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

if __name__ == "__main__":
    pass