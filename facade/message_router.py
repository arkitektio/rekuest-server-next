"""Transport-agnostic routing of FromAgent messages to the persist backend.

Both transports — the WebSocket ``AgentProtocol`` and the HTTP HookAgent intake — feed
their validated FromAgent messages through :func:`route_from_agent_message`. It performs
the side effects (persisting events, originating caller work) and **returns** the optional
reply message (``EventAck`` / ``CallerAssignResult``) rather than sending it, so each
transport delivers the reply its own way (over the socket, or in the HTTP response).

``HeartbeatEvent`` is intentionally NOT handled here — it is WebSocket-only liveness and
stays in ``AgentProtocol``.
"""

from __future__ import annotations

import logging
from typing import Optional

from facade import messages
from facade.capabilities import Capabilities
from facade.ports import PersistBackend

logger = logging.getLogger(__name__)


class UnknownAgentMessage(Exception):
    """Raised for a FromAgent message this router does not handle (caller decides the fate)."""


def _ack(message: messages.FromAgentEvent) -> messages.EventAck:
    """The durable-report acknowledgement so the agent can stop retaining a terminal report."""
    return messages.EventAck(
        event=message.id,
        assignation=getattr(message, "assignation", None),
        seq=getattr(message, "seq", None),
    )


async def route_from_agent_message(
    backend: PersistBackend,
    agent_id: int,
    capabilities: Optional[Capabilities],
    message: messages.FromAgentMessage,
    *,
    connection_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> Optional[messages.ToAgentMessage]:
    """Dispatch a FromAgent message and return the optional reply.

    Raises :class:`UnknownAgentMessage` for messages it does not handle (e.g. a second
    Register, Lock/Unlock) so the transport can close the socket / return a 4xx.
    """
    match message:
        case messages.CallerAssign():
            # A caller originating work. A bad request NACKs (returns an error result) rather
            # than propagating — it must never tear down the transport.
            try:
                assignation, created = await backend.on_caller_assign(
                    agent_id,
                    message,
                    can_assign_root=bool(capabilities and capabilities.can_assign_root),
                    connection_id=connection_id,
                    session_id=session_id,
                )
            except Exception as e:
                logger.error("CallerAssign failed", exc_info=True)
                return messages.CallerAssignResult(request=message.id, reference=message.reference, assignation=None, created=False, error=str(e))
            return messages.CallerAssignResult(request=message.id, reference=message.reference, assignation=str(assignation.pk), created=created)

        case messages.CancelledEvent():
            await backend.on_agent_cancelled(agent_id, message)
            return _ack(message)
        case messages.YieldEvent():
            await backend.on_agent_yield(agent_id, message)
            return None
        case messages.LogEvent():
            await backend.on_agent_log(agent_id, message)
            return None
        case messages.ProgressEvent():
            await backend.on_agent_progress(agent_id, message)
            return None
        case messages.DoneEvent():
            await backend.on_agent_done(agent_id, message)
            return _ack(message)
        case messages.ErrorEvent():
            await backend.on_agent_error(agent_id, message)
            return _ack(message)
        case messages.CriticalEvent():
            await backend.on_agent_critical(agent_id, message)
            return _ack(message)
        case messages.StatePatchEvent():
            await backend.on_agent_state_patch(agent_id, message)
            return None
        case messages.StateSnapshotEvent():
            await backend.on_agent_state_snapshot(agent_id, message)
            return None
        case messages.SessionInitMessage():
            await backend.on_agent_session_init(agent_id, message)
            return None
        case _:
            raise UnknownAgentMessage(type(message).__name__)
