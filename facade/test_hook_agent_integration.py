"""Integration test for hook agent functionality."""

import json
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock
import aiohttp
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from authentikate.models import Client
from facade import models, inputs
from facade.backend import controll_backend
from facade.mutations.agent import AgentInput, ensure_agent

User = get_user_model()


class HookAgentIntegrationTest(TransactionTestCase):
    """Integration test demonstrating complete hook agent workflow."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(username='testuser')
        self.client_obj = Client.objects.create(name='testclient')
        
        # Create a registry
        self.registry = models.Registry.objects.create(
            user=self.user,
            client=self.client_obj
        )
        
        # Mock info object
        self.info = type('Info', (), {
            'context': type('Context', (), {
                'request': type('Request', (), {
                    'user': self.user,
                    'client': self.client_obj
                })()
            })()
        })()
        
    def test_complete_hook_agent_workflow(self):
        """Test the complete workflow of hook agent registration and task assignment."""
        
        # Step 1: Register a hook agent
        hook_agent = asyncio.run(self._register_hook_agent())
        self.assertTrue(hook_agent.is_hook_agent)
        self.assertEqual(hook_agent.hook_endpoint, "http://example.com/webhook")
        
        # Step 2: Create an action and implementation for the hook agent
        collection = models.Collection.objects.create(
            name="Test Collection",
            description="Test collection",
            creator=self.user
        )
        
        action = models.Action.objects.create(
            name="Test Action",
            description="Test action",
            collection=collection,
            hash="test_action_hash",
            interface={"type": "function"},
            extension={"type": "python"}
        )
        
        implementation = models.Implementation.objects.create(
            action=action,
            agent=hook_agent,
            interface={"type": "function"},
            extension={"type": "python"}
        )
        
        # Step 3: Mock HTTP POST request to hook agent
        with patch('aiohttp.ClientSession.post') as mock_post:
            # Mock successful HTTP response
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.__aenter__.return_value = mock_response
            mock_post.return_value = mock_response
            
            # Step 4: Assign a task to the hook agent
            assignment_input = inputs.AssignInputModel(
                implementation=implementation.id,
                args={"input": "test_data"},
                reference="test_assignment",
                instance_id="test_instance"
            )
            
            assignation = controll_backend.assign(self.info, assignment_input)
            
            # Verify assignment was created
            self.assertIsNotNone(assignation)
            self.assertEqual(assignation.agent, hook_agent)
            
            # Give a moment for the async task to execute
            asyncio.run(asyncio.sleep(0.1))
            
            # Verify HTTP POST was called
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            
            # Verify the endpoint
            self.assertEqual(call_args[1]['url'], "http://example.com/webhook")
            
            # Verify the payload
            payload = call_args[1]['json']
            self.assertEqual(payload['type'], 'ASSIGN')
            self.assertEqual(payload['agent_id'], str(hook_agent.id))
            self.assertEqual(payload['message']['assignation'], str(assignation.id))
            self.assertEqual(payload['message']['args'], {"input": "test_data"})
            
            # Verify the headers
            headers = call_args[1]['headers']
            self.assertEqual(headers['Authorization'], 'Bearer test_secret_token')
            self.assertEqual(headers['Content-Type'], 'application/json')
        
        # Step 5: Test hook agent reporting back via REST API
        response = self.client.post(
            '/api/hook-agent/events/',
            data=json.dumps({
                'assignation_id': str(assignation.id),
                'event_type': 'PROGRESS',
                'progress': 50,
                'message': 'Half way done'
            }),
            HTTP_AUTHORIZATION='Bearer test_secret_token',
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'ok')
        
        # Step 6: Test completion event
        response = self.client.post(
            '/api/hook-agent/events/',
            data=json.dumps({
                'assignation_id': str(assignation.id),
                'event_type': 'DONE',
                'returns': {'result': 'success', 'output': 'processed_data'}
            }),
            HTTP_AUTHORIZATION='Bearer test_secret_token',
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'ok')
    
    def test_hook_agent_vs_regular_agent(self):
        """Test that regular agents still work via WebSocket while hook agents use HTTP."""
        
        # Create a regular agent
        regular_agent = asyncio.run(self._register_regular_agent())
        self.assertFalse(regular_agent.is_hook_agent)
        
        # Create a hook agent
        hook_agent = asyncio.run(self._register_hook_agent())
        self.assertTrue(hook_agent.is_hook_agent)
        
        # Create action and implementations
        collection = models.Collection.objects.create(
            name="Test Collection",
            description="Test collection",
            creator=self.user
        )
        
        action = models.Action.objects.create(
            name="Test Action",
            description="Test action",
            collection=collection,
            hash="test_action_hash",
            interface={"type": "function"},
            extension={"type": "python"}
        )
        
        regular_impl = models.Implementation.objects.create(
            action=action,
            agent=regular_agent,
            interface={"type": "function"},
            extension={"type": "python"}
        )
        
        hook_impl = models.Implementation.objects.create(
            action=action,
            agent=hook_agent,
            interface={"type": "function"},
            extension={"type": "python"}
        )
        
        # Test assignment to regular agent (should use WebSocket broadcast)
        with patch('facade.consumers.async_consumer.AgentConsumer.broadcast') as mock_broadcast:
            assignment_input = inputs.AssignInputModel(
                implementation=regular_impl.id,
                args={"input": "test_data"},
                reference="test_regular_assignment",
                instance_id="test_instance"
            )
            
            assignation = controll_backend.assign(self.info, assignment_input)
            
            # Give a moment for the async task to execute
            asyncio.run(asyncio.sleep(0.1))
            
            # Verify WebSocket broadcast was called
            mock_broadcast.assert_called_once()
            
        # Test assignment to hook agent (should use HTTP POST)
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.__aenter__.return_value = mock_response
            mock_post.return_value = mock_response
            
            assignment_input = inputs.AssignInputModel(
                implementation=hook_impl.id,
                args={"input": "test_data"},
                reference="test_hook_assignment",
                instance_id="test_instance"
            )
            
            assignation = controll_backend.assign(self.info, assignment_input)
            
            # Give a moment for the async task to execute
            asyncio.run(asyncio.sleep(0.1))
            
            # Verify HTTP POST was called
            mock_post.assert_called_once()
    
    async def _register_hook_agent(self):
        """Helper to register a hook agent."""
        input_data = AgentInput(
            instance_id="test_hook_agent",
            name="Test Hook Agent",
            is_hook_agent=True,
            hook_endpoint="http://example.com/webhook",
            hook_secret_token="test_secret_token",
        )
        
        return await ensure_agent(self.info, input_data)
    
    async def _register_regular_agent(self):
        """Helper to register a regular agent."""
        input_data = AgentInput(
            instance_id="test_regular_agent",
            name="Test Regular Agent",
            is_hook_agent=False,
            extensions=["test_ext"],
        )
        
        return await ensure_agent(self.info, input_data)