#!/usr/bin/env python3
"""
Setup script for the example hook agent.

This script demonstrates how to register a hook agent with the Rekuest server.
"""

import requests
import json
import sys

# Configuration - update these values for your setup
REKUEST_GRAPHQL_URL = "http://localhost:8000/graphql"
HOOK_ENDPOINT = "http://localhost:5000/webhook"
SECRET_TOKEN = "my-secret-hook-token-123"
AGENT_NAME = "Example Hook Agent"
INSTANCE_ID = "example-hook-agent"

# Your authentication token for GraphQL API
# In a real setup, you'd get this from your authentication system
AUTH_TOKEN = "your-auth-token-here"

def register_hook_agent():
    """Register the hook agent with Rekuest server."""
    
    query = """
    mutation EnsureHookAgent($input: AgentInput!) {
        ensureAgent(input: $input) {
            id
            name
            instanceId
            isHookAgent
            hookEndpoint
        }
    }
    """
    
    variables = {
        "input": {
            "instanceId": INSTANCE_ID,
            "name": AGENT_NAME,
            "isHookAgent": True,
            "hookEndpoint": HOOK_ENDPOINT,
            "hookSecretToken": SECRET_TOKEN
        }
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {AUTH_TOKEN}"
    }
    
    payload = {
        "query": query,
        "variables": variables
    }
    
    try:
        print(f"Registering hook agent '{AGENT_NAME}'...")
        print(f"Hook endpoint: {HOOK_ENDPOINT}")
        
        response = requests.post(
            REKUEST_GRAPHQL_URL,
            json=payload,
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            
            if "errors" in result:
                print("❌ GraphQL errors:")
                for error in result["errors"]:
                    print(f"   {error['message']}")
                return False
            
            agent = result["data"]["ensureAgent"]
            print("✅ Hook agent registered successfully!")
            print(f"   Agent ID: {agent['id']}")
            print(f"   Name: {agent['name']}")
            print(f"   Instance ID: {agent['instanceId']}")
            print(f"   Is Hook Agent: {agent['isHookAgent']}")
            print(f"   Hook Endpoint: {agent['hookEndpoint']}")
            return True
            
        else:
            print(f"❌ HTTP error: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error registering hook agent: {e}")
        return False

def test_hook_endpoint():
    """Test if the hook endpoint is accessible."""
    try:
        print(f"\nTesting hook endpoint: {HOOK_ENDPOINT}")
        
        # Try to reach the health endpoint
        health_url = HOOK_ENDPOINT.replace('/webhook', '/health')
        response = requests.get(health_url, timeout=5)
        
        if response.status_code == 200:
            print("✅ Hook endpoint is accessible")
            return True
        else:
            print(f"⚠️  Hook endpoint returned: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Hook endpoint not accessible: {e}")
        print("   Make sure the example_hook_agent.py is running")
        return False

def main():
    """Main setup function."""
    print("🚀 Hook Agent Setup")
    print("===================")
    
    if AUTH_TOKEN == "your-auth-token-here":
        print("❌ Please update the AUTH_TOKEN in this script with your actual token")
        return
    
    # Test hook endpoint
    endpoint_ok = test_hook_endpoint()
    
    # Register agent
    if register_hook_agent():
        print("\n🎉 Setup completed successfully!")
        print("\nNext steps:")
        print("1. Make sure your hook agent server is running")
        print("2. Create and assign tasks to your hook agent")
        print("3. Monitor the logs to see task assignments being processed")
        
        if not endpoint_ok:
            print("\n⚠️  Note: Hook endpoint test failed, but registration succeeded.")
            print("   Make sure to start your hook agent server to receive assignments.")
    else:
        print("\n❌ Setup failed. Please check the error messages above.")

if __name__ == "__main__":
    main()