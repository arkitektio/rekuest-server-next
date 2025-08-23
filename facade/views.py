"""Views for handling webhook agent responses."""

import json
import logging
from typing import Any, Dict

from django.http import JsonResponse, HttpRequest, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View
from authentikate.utils import authenticate_token_or_none
from authentikate.expand import aexpand_user_from_token, aexpand_client_from_token, aexpand_organization_from_token

from facade import models, messages
from facade.persist_backend import persist_backend

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name='dispatch')
class WebhookAgentEventView(View):
    """Handle webhook agent event responses."""

    async def post(self, request: HttpRequest) -> JsonResponse:
        """Handle POST requests from webhook agents."""
        try:
            # Parse request body
            body = json.loads(request.body.decode('utf-8'))
            agent_id = body.get('agent_id')
            message_data = body.get('message')
            
            if not agent_id or not message_data:
                return JsonResponse({'error': 'Missing agent_id or message'}, status=400)

            # Validate agent and secret
            auth_header = request.META.get('HTTP_AUTHORIZATION', '')
            secret_header = request.META.get('HTTP_X_AGENT_SECRET', '')
            
            if not auth_header.startswith('Bearer ') and not secret_header:
                return JsonResponse({'error': 'Missing authorization'}, status=401)

            # Get the agent
            try:
                agent = await models.Agent.objects.aget(id=agent_id)
            except models.Agent.DoesNotExist:
                return JsonResponse({'error': 'Agent not found'}, status=404)

            # Validate secret
            provided_secret = auth_header.replace('Bearer ', '') if auth_header.startswith('Bearer ') else secret_header
            if provided_secret != agent.hook_url_secret:
                return JsonResponse({'error': 'Invalid secret'}, status=401)

            # Parse and validate the message
            try:
                message = self._parse_agent_message(message_data)
            except ValueError as e:
                return JsonResponse({'error': f'Invalid message format: {str(e)}'}, status=400)

            # Process the message
            await self._process_agent_message(agent, message)
            
            return JsonResponse({'status': 'success'})
            
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            logger.error(f"Error processing webhook agent event: {e}", exc_info=True)
            return JsonResponse({'error': 'Internal server error'}, status=500)

    def _parse_agent_message(self, message_data: Dict[str, Any]) -> messages.FromAgentMessage:
        """Parse and validate agent message."""
        message_type = message_data.get('type')
        
        if message_type == messages.FromAgentMessageType.CANCELLED:
            return messages.CancelledEvent(**message_data)
        elif message_type == messages.FromAgentMessageType.YIELD:
            return messages.YieldEvent(**message_data)
        elif message_type == messages.FromAgentMessageType.LOG:
            return messages.LogEvent(**message_data)
        elif message_type == messages.FromAgentMessageType.PROGRESS:
            return messages.ProgressEvent(**message_data)
        elif message_type == messages.FromAgentMessageType.DONE:
            return messages.DoneEvent(**message_data)
        elif message_type == messages.FromAgentMessageType.ERROR:
            return messages.ErrorEvent(**message_data)
        elif message_type == messages.FromAgentMessageType.CRITICAL:
            return messages.CriticalEvent(**message_data)
        else:
            raise ValueError(f"Unsupported message type: {message_type}")

    async def _process_agent_message(self, agent: models.Agent, message: messages.FromAgentMessage) -> None:
        """Process the agent message using the same logic as websocket agents."""
        match message:
            case messages.CancelledEvent():
                await persist_backend.on_agent_cancelled(agent.id, message)
            case messages.YieldEvent():
                await persist_backend.on_agent_yield(agent.id, message)
            case messages.LogEvent():
                await persist_backend.on_agent_log(agent.id, message)
            case messages.ProgressEvent():
                await persist_backend.on_agent_progress(agent.id, message)
            case messages.DoneEvent():
                await persist_backend.on_agent_done(agent.id, message)
            case messages.ErrorEvent():
                await persist_backend.on_agent_error(agent.id, message)
            case messages.CriticalEvent():
                await persist_backend.on_agent_critical(agent.id, message)
            case _:
                logger.warning(f"Unhandled message type from webhook agent: {type(message)}")