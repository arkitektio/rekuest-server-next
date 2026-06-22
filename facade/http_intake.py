"""HTTP POST intake — the upstream transport for HookAgents.

A HookAgent POSTs the same FromAgent messages a websocket agent would send (reporting events
like Done/Yield/Progress, and ``CallerAssign`` for server-to-server origination) to
``POST /agi/http/<agent_id>``, HMAC-signed with the agent's ``hook_url_secret``. The request
is verified, parsed, and routed through the SAME :func:`route_from_agent_message` the socket
uses; the reply (``EventAck`` / ``CallerAssignResult``) is returned in the HTTP response.
"""

from __future__ import annotations

import json
import logging

from django.http import HttpRequest, HttpResponse, JsonResponse

from facade import capabilities, enums, hooks, models
from facade.consumers.agent_protocol import FromAgentPayload
from facade.hooks import SIGNATURE_HEADER
from facade.message_router import UnknownAgentMessage, route_from_agent_message
from facade.persist_backend import persist_backend

logger = logging.getLogger(__name__)


async def hook_intake(request: HttpRequest, agent_id: str) -> HttpResponse:
    """Authenticate (HMAC), validate, and route one FromAgent message from a HookAgent."""
    if request.method != "POST":
        return HttpResponse(status=405)

    body = request.body  # raw bytes — the exact bytes the HMAC was computed over

    agent = await models.Agent.objects.filter(id=agent_id, kind=enums.AgentKind.WEBHOOK.value).afirst()
    if agent is None:
        return JsonResponse({"error": "Unknown hook agent"}, status=404)
    if agent.blocked:
        return JsonResponse({"error": "Agent is blocked"}, status=403)
    if not hooks.verify(agent.hook_url_secret, body, request.headers.get(SIGNATURE_HEADER)):
        return JsonResponse({"error": "Invalid signature"}, status=401)

    try:
        payload = FromAgentPayload(message=json.loads(body))
    except Exception as e:
        return JsonResponse({"error": f"Invalid message: {e}"}, status=400)

    # No JWT on the HTTP path, so capabilities come from the lenient default (full while
    # enforcement is off). A per-agent scopes field can tighten this later.
    caps = capabilities.capabilities_from_scopes([])

    try:
        reply = await route_from_agent_message(persist_backend, agent.pk, caps, payload.message)
    except UnknownAgentMessage as e:
        return JsonResponse({"error": f"Unhandled message: {e}"}, status=400)
    except Exception as e:
        logger.error("Hook intake failed", exc_info=True)
        return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse(reply.model_dump() if reply is not None else {})
