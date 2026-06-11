"""Transport-agnostic agent protocol (the Humble Object).

All of the agent conversation logic lives here as a plain object with injected
dependencies — it knows nothing about Django Channels or WebSockets. ``send`` and
``close`` are callables wired by the adapter (``AgentConsumer``); ``backend`` and
``queue`` are ports; ``authenticator`` resolves a registration to an agent.

Because every collaborator is injected, the protocol/lifecycle/heartbeat
behaviour is unit-testable with fakes — no docker, no DB, no monkeypatching.
"""

import asyncio
import datetime
import json
import logging
from typing import Awaitable, Callable, List, Optional

from authentikate.expand import (
    aexpand_client_from_token,
    aexpand_organization_from_token,
    aexpand_user_from_token,
)
from authentikate.utils import authenticate_token_or_none
from django.conf import settings
from pydantic import BaseModel, Field

from facade import codes, messages, models
from facade.consumers.agent_queue import AgentQueue
from facade.persist_backend import persist_backend

logger = logging.getLogger(__name__)

SendCallable = Callable[[str], Awaitable[None]]
CloseCallable = Callable[[int], Awaitable[None]]
Authenticator = Callable[[messages.Register], Awaitable["models.Agent"]]


class FromAgentPayload(BaseModel):
    """Pydantic model representing the payload sent by the agent."""

    message: messages.FromAgentMessage = Field(discriminator="type")


async def default_authenticator(register: messages.Register) -> "models.Agent":
    """Resolve a ``Register`` to its ``Agent`` via the token identity.

    NOTE: the ``aget_or_create`` create-branch omits the required
    ``app``/``release``/``device`` columns, so this can only *find* an
    already-created agent (created out-of-band via the ``ensureAgent`` mutation).
    That is pinned behaviour — do not "fix" it here without updating
    ``test_register_for_uncreated_agent_is_rejected``.
    """
    token = authenticate_token_or_none(register.token)
    if not token:
        raise ValueError("Invalid token")

    user = await aexpand_user_from_token(token)
    client = await aexpand_client_from_token(token)
    organization = await aexpand_organization_from_token(token)

    registry, _ = await models.Registry.objects.aget_or_create(
        client=client,
        user=user,
        organization=organization,
    )

    agent, _ = await models.Agent.objects.aget_or_create(
        registry=registry,
        instance_id=register.instance_id or "default",
        defaults=dict(
            name=f"{str(registry.pk)} on {register.instance_id}",
        ),
    )
    return agent


class AgentProtocol:
    """Drives the agent conversation over injected transport + ports."""

    def __init__(
        self,
        *,
        send: SendCallable,
        close: CloseCallable,
        queue: AgentQueue,
        backend=persist_backend,
        authenticator: Authenticator = default_authenticator,
        heartbeat_interval: Optional[float] = None,
        heartbeat_timeout: Optional[float] = None,
    ) -> None:
        self.send = send
        self.close = close
        self.queue = queue
        self.backend = backend
        self.authenticator = authenticator
        self.heartbeat_interval = (
            heartbeat_interval if heartbeat_interval is not None else settings.AGENT_HEARTBEAT_INTERVAL
        )
        self.heartbeat_timeout = (
            heartbeat_timeout if heartbeat_timeout is not None else settings.AGENT_HEARTBEAT_RESPONSE_TIMEOUT
        )

        self.agent: Optional["models.Agent"] = None
        self.assignations: List["models.Assignation"] = []
        self.received_initial_payload = False
        self.heartbeat_future: Optional[asyncio.Future] = None
        self.listen_task: Optional[asyncio.Task] = None
        self.heartbeat_task: Optional[asyncio.Task] = None
        # All outbound frames funnel through this lock. ``receive`` is serialized
        # by Channels, but the heartbeat and listen loops send concurrently with
        # it (and each other) on the same loop — without serialization their
        # frames could interleave on the wire. ``close`` deliberately stays
        # outside the lock and is never called while it is held (no deadlock).
        self._send_lock = asyncio.Lock()

    async def _send(self, text: str) -> None:
        """Single guarded path to the transport — the only place ``send`` is called."""
        async with self._send_lock:
            await self.send(text)

    async def send_to_agent_message(self, message: messages.ToAgentMessage) -> None:
        """Serialize and hand a message to the transport."""
        await self._send(message.model_dump_json())

    async def receive(self, text_data: Optional[str]) -> None:
        """Parse, validate and dispatch a single inbound frame."""
        try:
            raw = json.loads(text_data)
        except json.JSONDecodeError:
            logger.error("Error in agent", exc_info=True)
            await self.close(codes.FROM_AGENT_MESSAGE_IS_NOT_VALID_JSON_CODE)
            return

        try:
            payload = FromAgentPayload(message=raw)
        except Exception as e:
            logger.error(f"Error in agent {raw}", exc_info=True)
            await self.send_to_agent_message(messages.ProtocolError(error=str(e)))
            await self.close(codes.FROM_AGENT_MESSAGE_DOES_NOT_MATCH_SCHEMA_CODE)
            return

        try:
            if not self.received_initial_payload:
                if not isinstance(payload.message, messages.Register):
                    raise ValueError("First message must be a register")
                self.received_initial_payload = True
                await self.on_register(payload.message)
            else:
                await self.dispatch(payload.message)
        except Exception:
            logger.error("Unkown in consumer", exc_info=True)
            await self.close(codes.FROM_AGENT_MESSAGE_DOES_NOT_MATCH_SCHEMA_CODE)

    async def dispatch(self, message: messages.FromAgentMessage) -> None:
        """Route a validated, post-registration message to its handler."""
        agent_id = self.agent.pk
        match message:
            # A second Register after registration is a protocol violation: it must
            # NOT re-run on_register (that would orphan the first listen/heartbeat
            # task pair). Fall through to ``case _`` below and close.
            case messages.HeartbeatEvent():
                await self.on_agent_heartbeat()
            case messages.CancelledEvent():
                await self.backend.on_agent_cancelled(agent_id, message)
            case messages.YieldEvent():
                await self.backend.on_agent_yield(agent_id, message)
            case messages.LogEvent():
                await self.backend.on_agent_log(agent_id, message)
            case messages.ProgressEvent():
                await self.backend.on_agent_progress(agent_id, message)
            case messages.DoneEvent():
                await self.backend.on_agent_done(agent_id, message)
            case messages.ErrorEvent():
                await self.backend.on_agent_error(agent_id, message)
            case messages.CriticalEvent():
                await self.backend.on_agent_critical(agent_id, message)
            case messages.StatePatchEvent():
                await self.backend.on_agent_state_patch(agent_id, message)
            case messages.StateSnapshotEvent():
                await self.backend.on_agent_state_snapshot(agent_id, message)
            case messages.SessionInitMessage():
                await self.backend.on_agent_session_init(agent_id, message)
            case _:
                logger.error("Unknown message in agent")
                await self.close(codes.FROM_AGENT_MESSAGE_DOES_NOT_MATCH_SCHEMA_CODE)

    async def on_register(self, register: messages.Register) -> None:
        """Authenticate, send ``Init`` and spawn the background loops."""
        self.agent = await self.authenticator(register)

        if self.agent.blocked:
            await self.close(codes.AGENT_IS_BLOCKED_CODE)
            return

        self.assignations = await self.backend.on_agent_connected(self.agent.pk)
        self.heartbeat_future = None

        await self.send_to_agent_message(
            messages.Init(
                instance_id=self.agent.instance_id,
                agent=str(self.agent.pk),
                inquiries=[messages.AssignInquiry(assignation=str(a.pk)) for a in self.assignations],
            )
        )

        self.listen_task = asyncio.create_task(self.listen_for_tasks(self.agent.pk))
        self.heartbeat_task = asyncio.create_task(self.heartbeat(self.agent.pk))

    async def on_agent_heartbeat(self) -> None:
        """Record liveness and resolve the pending heartbeat future."""
        if not self.agent:
            raise Exception("Agent not registered")

        # Resolve the handshake BEFORE persisting. ``asave`` is a DB round-trip;
        # if it ran first a slow write could push resolution past the heartbeat
        # timeout and the loop would close a connection that actually answered.
        if self.heartbeat_future and not self.heartbeat_future.done():
            self.heartbeat_future.set_result(None)
            self.heartbeat_future = None
        else:
            logger.error("Received heartbeat without future, possible race condition.")

        self.agent.connected = True
        self.agent.last_seen = datetime.datetime.now()
        await self.agent.asave()

    async def heartbeat(self, agent_id: str) -> None:
        """Periodically ping the agent and close if it stops answering."""
        try:
            while True:
                await asyncio.sleep(self.heartbeat_interval)
                # Arm the future before sending so an answer always has a target.
                self.heartbeat_future = asyncio.Future()
                await self.send_to_agent_message(messages.Heartbeat())
                try:
                    await asyncio.wait_for(self.heartbeat_future, self.heartbeat_timeout)
                except asyncio.TimeoutError:
                    logger.error(f"Timeout on client {agent_id} for heartbeat")
                    await self.close(codes.HEARTBEAT_NOT_RESPONDED_CODE)
                    return
        except asyncio.CancelledError:
            return

    async def listen_for_tasks(self, agent_id: str) -> None:
        """Relay queued messages (e.g. from ``broadcast``) to the agent."""
        try:
            while True:
                task = await self.queue.pop(agent_id)
                if task:
                    # Deliver first, then ack — so a crash mid-delivery leaves the
                    # message recoverable (at-least-once), matching the original.
                    await self._send(task)
                    await self.queue.ack(task)
        except asyncio.CancelledError:
            return

    async def shutdown(self) -> None:
        """Cancel loops, mark the agent disconnected and release the queue."""
        for task in (self.listen_task, self.heartbeat_task):
            if task is None:
                continue
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            except Exception:
                logger.error("Error cancelling agent task", exc_info=True)

        if self.agent is not None:
            await self.backend.on_agent_disconnected(self.agent.pk)

        await self.queue.close()
