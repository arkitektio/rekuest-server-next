"""Tests for hook agent functionality."""

import json
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from authentikate.models import Client
from facade import models
from facade.mutations.agent import AgentInput, ensure_agent
from unittest.mock import patch, AsyncMock
import asyncio

User = get_user_model()


class HookAgentTest(TestCase):
    """Test hook agent functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(username='testuser')
        self.client = Client.objects.create(name='testclient')
        
    def test_ensure_hook_agent_validation(self):
        """Test that hook agent validation works correctly."""
        # Test hook agent with missing endpoint should fail
        with self.assertRaises(ValueError) as cm:
            asyncio.run(self._create_hook_agent_missing_endpoint())
        self.assertIn("hook_endpoint is required", str(cm.exception))
        
        # Test hook agent with missing token should fail
        with self.assertRaises(ValueError) as cm:
            asyncio.run(self._create_hook_agent_missing_token())
        self.assertIn("hook_secret_token is required", str(cm.exception))
    
    async def _create_hook_agent_missing_endpoint(self):
        """Helper to create hook agent without endpoint."""
        info = type('Info', (), {
            'context': type('Context', (), {
                'request': type('Request', (), {
                    'user': self.user,
                    'client': self.client
                })()
            })()
        })()
        
        input_data = AgentInput(
            instance_id="test_hook",
            name="Test Hook Agent",
            is_hook_agent=True,
            hook_endpoint=None,  # Missing
            hook_secret_token="secret123",
        )
        
        return await ensure_agent(info, input_data)
    
    async def _create_hook_agent_missing_token(self):
        """Helper to create hook agent without token."""
        info = type('Info', (), {
            'context': type('Context', (), {
                'request': type('Request', (), {
                    'user': self.user,
                    'client': self.client
                })()
            })()
        })()
        
        input_data = AgentInput(
            instance_id="test_hook",
            name="Test Hook Agent",
            is_hook_agent=True,
            hook_endpoint="http://example.com/hook",
            hook_secret_token=None,  # Missing
        )
        
        return await ensure_agent(info, input_data)
    
    def test_create_valid_hook_agent(self):
        """Test creating a valid hook agent."""
        agent = asyncio.run(self._create_valid_hook_agent())
        
        self.assertTrue(agent.is_hook_agent)
        self.assertEqual(agent.hook_endpoint, "http://example.com/hook")
        self.assertEqual(agent.hook_secret_token, "secret123")
        self.assertEqual(agent.name, "Test Hook Agent")
        self.assertEqual(agent.instance_id, "test_hook")
    
    async def _create_valid_hook_agent(self):
        """Helper to create a valid hook agent."""
        info = type('Info', (), {
            'context': type('Context', (), {
                'request': type('Request', (), {
                    'user': self.user,
                    'client': self.client
                })()
            })()
        })()
        
        input_data = AgentInput(
            instance_id="test_hook",
            name="Test Hook Agent",
            is_hook_agent=True,
            hook_endpoint="http://example.com/hook",
            hook_secret_token="secret123",
        )
        
        return await ensure_agent(info, input_data)
    
    def test_create_regular_agent(self):
        """Test creating a regular (non-hook) agent."""
        agent = asyncio.run(self._create_regular_agent())
        
        self.assertFalse(agent.is_hook_agent)
        self.assertIsNone(agent.hook_endpoint)
        self.assertIsNone(agent.hook_secret_token)
        self.assertEqual(agent.name, "Test Regular Agent")
        self.assertEqual(agent.instance_id, "test_regular")
    
    async def _create_regular_agent(self):
        """Helper to create a regular agent."""
        info = type('Info', (), {
            'context': type('Context', (), {
                'request': type('Request', (), {
                    'user': self.user,
                    'client': self.client
                })()
            })()
        })()
        
        input_data = AgentInput(
            instance_id="test_regular",
            name="Test Regular Agent",
            is_hook_agent=False,  # Regular agent
            extensions=["test_ext"],
        )
        
        return await ensure_agent(info, input_data)


class HookAgentAPITest(TestCase):
    """Test hook agent REST API endpoints."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(username='testuser')
        self.client_obj = Client.objects.create(name='testclient')
        
        # Create a registry
        self.registry = models.Registry.objects.create(
            user=self.user,
            client=self.client_obj
        )
        
        # Create a hook agent
        self.hook_agent = models.Agent.objects.create(
            registry=self.registry,
            instance_id="test_hook",
            name="Test Hook Agent",
            is_hook_agent=True,
            hook_endpoint="http://example.com/hook",
            hook_secret_token="test_secret_token",
        )
        
        # Create a regular assignation
        self.assignation = models.Assignation.objects.create(
            agent=self.hook_agent,
            args={},
            reference="test_ref",
            # Add other required fields as needed
        )
    
    def test_hook_agent_heartbeat_success(self):
        """Test successful heartbeat from hook agent."""
        response = self.client.post(
            '/api/hook-agent/heartbeat/',
            HTTP_AUTHORIZATION='Bearer test_secret_token',
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'ok')
    
    def test_hook_agent_heartbeat_unauthorized(self):
        """Test heartbeat with invalid token."""
        response = self.client.post(
            '/api/hook-agent/heartbeat/',
            HTTP_AUTHORIZATION='Bearer invalid_token',
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 401)
    
    def test_hook_agent_event_success(self):
        """Test successful event submission from hook agent."""
        event_data = {
            'assignation_id': str(self.assignation.id),
            'event_type': 'PROGRESS',
            'progress': 50,
            'message': 'Half way done'
        }
        
        response = self.client.post(
            '/api/hook-agent/events/',
            data=json.dumps(event_data),
            HTTP_AUTHORIZATION='Bearer test_secret_token',
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'ok')
    
    def test_hook_agent_event_unauthorized(self):
        """Test event submission with invalid token."""
        event_data = {
            'assignation_id': str(self.assignation.id),
            'event_type': 'PROGRESS',
            'progress': 50
        }
        
        response = self.client.post(
            '/api/hook-agent/events/',
            data=json.dumps(event_data),
            HTTP_AUTHORIZATION='Bearer invalid_token',
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 401)
    
    def test_hook_agent_event_invalid_assignation(self):
        """Test event submission with invalid assignation."""
        event_data = {
            'assignation_id': 'invalid_id',
            'event_type': 'PROGRESS',
            'progress': 50
        }
        
        response = self.client.post(
            '/api/hook-agent/events/',
            data=json.dumps(event_data),
            HTTP_AUTHORIZATION='Bearer test_secret_token',
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)