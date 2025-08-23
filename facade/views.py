"""REST API views for hook agent communication."""

import json
import logging
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseUnauthorized
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View
import asyncio

from facade import models, enums
from facade.persist_backend import persist_backend

logger = logging.getLogger(__name__)


def authenticate_hook_agent(request):
    """Authenticate a hook agent based on the Authorization header."""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return None
    
    token = auth_header[7:]  # Remove 'Bearer ' prefix
    
    try:
        # Find the agent with this hook secret token
        agent = models.Agent.objects.get(
            hook_secret_token=token,
            is_hook_agent=True
        )
        return agent
    except models.Agent.DoesNotExist:
        return None


@method_decorator(csrf_exempt, name='dispatch')
class HookAgentEventView(View):
    """View for receiving assignment events from hook agents."""
    
    def post(self, request):
        """Handle assignment event updates from hook agents."""
        # Authenticate the hook agent
        agent = authenticate_hook_agent(request)
        if not agent:
            return HttpResponseUnauthorized('Invalid or missing authentication token')
        
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return HttpResponseBadRequest('Invalid JSON in request body')
        
        # Validate required fields
        required_fields = ['assignation_id', 'event_type']
        for field in required_fields:
            if field not in data:
                return HttpResponseBadRequest(f'Missing required field: {field}')
        
        assignation_id = data['assignation_id']
        event_type = data['event_type']
        
        # Validate assignation belongs to this agent
        try:
            assignation = models.Assignation.objects.get(
                id=assignation_id,
                agent=agent
            )
        except models.Assignation.DoesNotExist:
            return HttpResponseBadRequest(f'Assignation {assignation_id} not found or not assigned to this agent')
        
        # Handle different event types
        try:
            if event_type == 'PROGRESS':
                return self._handle_progress_event(agent, assignation, data)
            elif event_type == 'LOG':
                return self._handle_log_event(agent, assignation, data)
            elif event_type == 'DONE':
                return self._handle_done_event(agent, assignation, data)
            elif event_type == 'YIELD':
                return self._handle_yield_event(agent, assignation, data)
            elif event_type == 'ERROR':
                return self._handle_error_event(agent, assignation, data)
            elif event_type == 'CRITICAL':
                return self._handle_critical_event(agent, assignation, data)
            elif event_type == 'CANCELLED':
                return self._handle_cancelled_event(agent, assignation, data)
            else:
                return HttpResponseBadRequest(f'Unknown event type: {event_type}')
        except Exception as e:
            logger.error(f'Error processing event from hook agent {agent.id}: {e}')
            return JsonResponse({'error': 'Internal server error'}, status=500)
    
    def _handle_progress_event(self, agent, assignation, data):
        """Handle progress event from hook agent."""
        progress = data.get('progress', 0)
        message = data.get('message', '')
        
        # Run the async persist backend method
        asyncio.create_task(
            persist_backend.on_agent_progress(
                str(agent.id),
                type('ProgressEvent', (), {
                    'assignation': assignation.id,
                    'progress': progress,
                    'message': message
                })()
            )
        )
        
        return JsonResponse({'status': 'ok', 'message': 'Progress event recorded'})
    
    def _handle_log_event(self, agent, assignation, data):
        """Handle log event from hook agent."""
        log_message = data.get('message', '')
        level = data.get('level', 'INFO')
        
        # Run the async persist backend method  
        asyncio.create_task(
            persist_backend.on_agent_log(
                str(agent.id),
                type('LogEvent', (), {
                    'assignation': assignation.id,
                    'message': log_message,
                    'level': level
                })()
            )
        )
        
        return JsonResponse({'status': 'ok', 'message': 'Log event recorded'})
    
    def _handle_done_event(self, agent, assignation, data):
        """Handle done event from hook agent."""
        returns = data.get('returns')
        
        # Run the async persist backend method
        asyncio.create_task(
            persist_backend.on_agent_done(
                str(agent.id),
                type('DoneEvent', (), {
                    'assignation': assignation.id,
                    'returns': returns
                })()
            )
        )
        
        return JsonResponse({'status': 'ok', 'message': 'Done event recorded'})
    
    def _handle_yield_event(self, agent, assignation, data):
        """Handle yield event from hook agent."""
        returns = data.get('returns')
        
        # Run the async persist backend method
        asyncio.create_task(
            persist_backend.on_agent_yield(
                str(agent.id),
                type('YieldEvent', (), {
                    'assignation': assignation.id,
                    'returns': returns
                })()
            )
        )
        
        return JsonResponse({'status': 'ok', 'message': 'Yield event recorded'})
    
    def _handle_error_event(self, agent, assignation, data):
        """Handle error event from hook agent."""
        error_message = data.get('message', '')
        
        # Run the async persist backend method
        asyncio.create_task(
            persist_backend.on_agent_error(
                str(agent.id),
                type('ErrorEvent', (), {
                    'assignation': assignation.id,
                    'message': error_message
                })()
            )
        )
        
        return JsonResponse({'status': 'ok', 'message': 'Error event recorded'})
    
    def _handle_critical_event(self, agent, assignation, data):
        """Handle critical event from hook agent."""
        error_message = data.get('message', '')
        
        # Run the async persist backend method
        asyncio.create_task(
            persist_backend.on_agent_critical(
                str(agent.id),
                type('CriticalEvent', (), {
                    'assignation': assignation.id,
                    'message': error_message
                })()
            )
        )
        
        return JsonResponse({'status': 'ok', 'message': 'Critical event recorded'})
    
    def _handle_cancelled_event(self, agent, assignation, data):
        """Handle cancelled event from hook agent."""
        message = data.get('message', '')
        
        # Run the async persist backend method
        asyncio.create_task(
            persist_backend.on_agent_cancelled(
                str(agent.id),
                type('CancelledEvent', (), {
                    'assignation': assignation.id,
                    'message': message
                })()
            )
        )
        
        return JsonResponse({'status': 'ok', 'message': 'Cancelled event recorded'})


@method_decorator(csrf_exempt, name='dispatch')
class HookAgentHeartbeatView(View):
    """View for receiving heartbeat from hook agents."""
    
    def post(self, request):
        """Handle heartbeat from hook agents."""
        # Authenticate the hook agent
        agent = authenticate_hook_agent(request)
        if not agent:
            return HttpResponseUnauthorized('Invalid or missing authentication token')
        
        try:
            # Run the async persist backend method
            asyncio.create_task(
                persist_backend.on_agent_heartbeat(str(agent.id))
            )
            
            return JsonResponse({'status': 'ok', 'message': 'Heartbeat recorded'})
        except Exception as e:
            logger.error(f'Error processing heartbeat from hook agent {agent.id}: {e}')
            return JsonResponse({'error': 'Internal server error'}, status=500)