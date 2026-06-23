"""Transport-agnostic routing of FromAgent messages to the persist backend.

Both transports — the WebSocket ``AgentProtocol`` and the HTTP HookAgent intake — feed
their validated FromAgent messages through :func:`route_from_agent_message`. It performs
the side effects (persisting events, originating caller work) and **returns** the optional
reply message (``EventAck`` / ``AssignResponse``) rather than sending it, so each
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
        task=getattr(message, "task", None),
        seq=getattr(message, "seq", None),
    )


async def _control(op, agent_id, message, connection_id, session_id) -> messages.ControlResponse:
    """Run a caller lifecycle-control request and return its ack (NACK on error, never raise)."""
    try:
        task = await op(agent_id, message, connection_id=connection_id, session_id=session_id)
    except Exception as e:
        logger.error("Caller control request failed", exc_info=True)
        return messages.ControlResponse(request=message.id, task=message.task, accepted=False, error=str(e))
    return messages.ControlResponse(request=message.id, task=str(task.pk), accepted=True)


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
        case messages.AssignRequest():
            # A caller originating work. A bad request NACKs (returns an error result) rather
            # than propagating — it must never tear down the transport.
            try:
                task, created = await backend.on_caller_assign(
                    agent_id,
                    message,
                    can_assign_root=bool(capabilities and capabilities.can_assign_root),
                    connection_id=connection_id,
                    session_id=session_id,
                )
            except Exception as e:
                logger.error("AssignRequest failed", exc_info=True)
                return messages.AssignResponse(request=message.id, reference=message.reference, task=None, created=False, error=str(e))
            return messages.AssignResponse(request=message.id, reference=message.reference, task=str(task.pk), created=created)

        # Caller lifecycle-control requests (two-phase; the outcome streams back as …Event mirrors).
        case messages.CancelRequest():
            return await _control(backend.on_caller_cancel, agent_id, message, connection_id, session_id)
        case messages.InterruptRequest():
            return await _control(backend.on_caller_interrupt, agent_id, message, connection_id, session_id)
        case messages.PauseRequest():
            return await _control(backend.on_caller_pause, agent_id, message, connection_id, session_id)
        case messages.ResumeRequest():
            return await _control(backend.on_caller_resume, agent_id, message, connection_id, session_id)

        # Lifecycle confirmation events from the executing agent.
        case messages.Started():
            await backend.on_agent_started(agent_id, message)
            return _ack(message)
        case messages.Cancelled():
            await backend.on_agent_cancelled(agent_id, message)
            return _ack(message)
        case messages.Interrupted():
            await backend.on_agent_interrupted(agent_id, message)
            return _ack(message)
        case messages.Paused():
            await backend.on_agent_paused(agent_id, message)
            return _ack(message)
        case messages.Resumed():
            await backend.on_agent_resumed(agent_id, message)
            return _ack(message)
        case messages.Yield():
            await backend.on_agent_yield(agent_id, message)
            return None
        case messages.Log():
            await backend.on_agent_log(agent_id, message)
            return None
        case messages.Progress():
            await backend.on_agent_progress(agent_id, message)
            return None
        case messages.Completed():
            await backend.on_agent_done(agent_id, message)
            return _ack(message)
        case messages.Failed():
            await backend.on_agent_error(agent_id, message)
            return _ack(message)
        case messages.Critical():
            await backend.on_agent_critical(agent_id, message)
            return _ack(message)
        case messages.StatePatch():
            await backend.on_agent_state_patch(agent_id, message)
            return None
        case messages.StateSnapshot():
            await backend.on_agent_state_snapshot(agent_id, message)
            return None
        case messages.SessionInit():
            await backend.on_agent_session_init(agent_id, message)
            return None
        case _:
            raise UnknownAgentMessage(type(message).__name__)
