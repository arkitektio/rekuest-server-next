"""Transport-agnostic agent protocol (the Humble Object).

All of the agent conversation logic lives here as a plain object with injected
dependencies — it knows nothing about Django Channels or WebSockets. ``send`` and
``close`` are callables wired by the adapter (``AgentConsumer``); ``backend`` and
``queue`` are ports; ``authenticator`` resolves a registration to an agent.

Because every collaborator is injected, the protocol/lifecycle/heartbeat
behaviour is unit-testable with fakes — no docker, no DB, no monkeypatching.
"""

import asyncio
import json
import logging
import uuid
from typing import Awaitable, Callable, Optional

from authentikate.expand import (
    aexpand_client_from_token,
    aexpand_organization_from_token,
    aexpand_user_from_token,
)
from authentikate.utils import authenticate_token_or_none
from django.conf import settings
from django.utils import timezone
from pydantic import BaseModel, Field

from facade import capabilities, codes, messages, models
from facade.capabilities import Capabilities
from facade.consumers.agent_queue import AgentQueue
from facade.message_router import UnknownAgentMessage, route_from_agent_message
from facade.persist_backend import persist_backend
from facade.ports import PersistBackend

logger = logging.getLogger(__name__)

SendCallable = Callable[[str], Awaitable[None]]
CloseCallable = Callable[[int], Awaitable[None]]
# The authenticator resolves a Register to the durable agent identity AND the
# capabilities granted by its token scopes (the two are decided together, from the
# same token, so the protocol never has to re-authenticate to learn capabilities).
Authenticator = Callable[[messages.Register], Awaitable[tuple["models.Agent", Capabilities]]]
# Wired by the adapter so the protocol can join the agent's connection group and
# displace other live connections — both are no-ops by default (unit tests).
RegisterConnectionCallable = Callable[[str], Awaitable[None]]
KickOthersCallable = Callable[[], Awaitable[None]]
# Wired by the adapter so the protocol can join the caller event group
# (``ass_caller_{caller_id}``) and receive the events of work it originated.
RegisterCallerCallable = Callable[[str], Awaitable[None]]


async def _noop_register_connection(agent_id: str) -> None:
    return None


async def _noop_kick_others() -> None:
    return None


async def _noop_register_caller(caller_id: str) -> None:
    return None


class FromAgentPayload(BaseModel):
    """Pydantic model representing the payload sent by the agent."""

    message: messages.FromAgentMessage = Field(discriminator="type")


async def default_authenticator(register: messages.Register) -> tuple["models.Agent", Capabilities]:
    """Resolve a ``Register`` to its ``Agent`` + granted ``Capabilities`` via the token.

    NOTE: the ``aget_or_create`` create-branch omits the required
    ``app``/``release`` columns, so this can only *find* an
    already-created agent (created out-of-band via the ``ensureAgent`` mutation).
    That is pinned behaviour — do not "fix" it here without updating
    ``test_register_for_uncreated_agent_is_rejected``.
    """
    token = await authenticate_token_or_none(register.token)
    if not token:
        raise ValueError("Invalid token")

    user = await aexpand_user_from_token(token)
    client = await aexpand_client_from_token(token)
    organization = await aexpand_organization_from_token(token)

    agent, _ = await models.Agent.objects.aget_or_create(
        client=client,
        user=user,
        organization=organization,
        defaults=dict(
            name=f"{client.client_id}",
        ),
    )
    caps = capabilities.capabilities_from_scopes(getattr(token, "scopes", []))
    return agent, caps


class AgentProtocol:
    """Drives the agent conversation over injected transport + ports."""

    def __init__(
        self,
        *,
        send: SendCallable,
        close: CloseCallable,
        queue: AgentQueue,
        backend: PersistBackend = persist_backend,
        authenticator: Authenticator = default_authenticator,
        register_connection: RegisterConnectionCallable = _noop_register_connection,
        kick_others: KickOthersCallable = _noop_kick_others,
        register_caller: RegisterCallerCallable = _noop_register_caller,
        connection_id: Optional[str] = None,
        heartbeat_interval: Optional[float] = None,
        heartbeat_timeout: Optional[float] = None,
    ) -> None:
        self.send = send
        self.close = close
        self.queue = queue
        self.backend = backend
        self.authenticator = authenticator
        self.register_connection = register_connection
        self.kick_others = kick_others
        self.register_caller = register_caller
        # Identifies this connection so the backend can tell, on disconnect,
        # whether we are still the agent's active connection or were displaced.
        self.connection_id = connection_id or str(uuid.uuid4())
        self.heartbeat_interval = (
            heartbeat_interval if heartbeat_interval is not None else settings.AGENT_HEARTBEAT_INTERVAL
        )
        self.heartbeat_timeout = (
            heartbeat_timeout if heartbeat_timeout is not None else settings.AGENT_HEARTBEAT_RESPONSE_TIMEOUT
        )

        self.agent: Optional["models.Agent"] = None
        # Resolved at register: the granted capabilities, the requested mode, whether this
        # connection is the executor singleton, and the executor's volatile process id.
        self.capabilities: Optional[Capabilities] = None
        self.mode: messages.AgentMode = messages.AgentMode.EXECUTOR
        self.executes_work: bool = False
        self.session_id: Optional[str] = None
        # The durable caller id whose event group this connection joined (any mode may
        # originate work and must receive its results back over this socket).
        self.caller_id: Optional[str] = None
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
            logger.error("Unknown error handling agent message", exc_info=True)
            await self.close(codes.FROM_AGENT_MESSAGE_DOES_NOT_MATCH_SCHEMA_CODE)

    async def dispatch(self, message: messages.FromAgentMessage) -> None:
        """Route a validated, post-registration message to its handler.

        ``HeartbeatEvent`` is WS-only liveness and handled here; everything else goes through
        the shared :func:`route_from_agent_message` (the same router the HTTP HookAgent intake
        uses) and its returned reply is sent over the socket. A second Register / Lock / etc.
        raises ``UnknownAgentMessage`` and closes the connection.
        """
        if isinstance(message, messages.HeartbeatEvent):
            await self.on_agent_heartbeat()
            return

        try:
            reply = await route_from_agent_message(
                self.backend,
                self.agent.pk,
                self.capabilities,
                message,
                connection_id=self.connection_id,
                session_id=self.session_id,
            )
        except UnknownAgentMessage:
            logger.error("Unknown message in agent")
            await self.close(codes.FROM_AGENT_MESSAGE_DOES_NOT_MATCH_SCHEMA_CODE)
            return

        if reply is not None:
            await self.send_to_agent_message(reply)

    async def on_register(self, register: messages.Register) -> None:
        """Authenticate, authorize the requested mode, send ``Init`` and spawn loops.

        Gate order (each gate may close and return): authenticate → blocked → mode
        authorization → conflict/displacement (executors only) → connect + Init + loops.
        """
        self.agent, self.capabilities = await self.authenticator(register)
        self.mode = messages.AgentMode(register.mode)
        self.session_id = register.session_id
        self.executes_work = capabilities.mode_executes_work(self.mode)

        if self.agent.blocked:
            await self.close(codes.AGENT_IS_BLOCKED_CODE)
            return

        # Capabilities come from the token, never self-declaration: a participant may
        # only operate in a mode its scopes cover.
        if not capabilities.authorize_mode(self.capabilities, self.mode):
            await self.send_to_agent_message(
                messages.ProtocolError(error=f"Token is not authorized for mode {self.mode.value}.")
            )
            await self.close(codes.MODE_NOT_AUTHORIZED_CODE)
            return

        # Join the caller event group for EVERY mode: even a pure executor assigns
        # *dependent* work and must receive its results back over this socket. Done
        # before Init so no originated-work event is missed.
        self.caller_id = await self.backend.get_or_create_caller_id(self.agent.pk)
        await self.register_caller(self.caller_id)

        # Caller reclaim: cancel any pending caller-death cascade for this session and adopt
        # the roots it originated (runs for every mode — any participant may originate work).
        await self.backend.on_caller_connected(self.agent.pk, self.connection_id, self.session_id)

        self.heartbeat_future = None

        if self.executes_work:
            # The executor is a singleton: only one live connection per agent. Reject a
            # second unless ``force`` is set, in which case displace the incumbent.
            was_connected = self.agent.connected
            if was_connected and not register.force:
                await self.send_to_agent_message(
                    messages.ProtocolError(error="Another connection is already registered for this agent. Reconnect with force to take over.")
                )
                await self.close(codes.AGENT_ALREADY_CONNECTED_CODE)
                return

            # Join the agent's connection group first (so we can later be kicked).
            await self.register_connection(self.agent.pk)

            # Claim ownership (sets ``active_connection_id`` to us) BEFORE displacing the
            # incumbent. Order matters: the displaced connection's disconnect handler is
            # guarded on ``active_connection_id`` — if we kicked before claiming, it could
            # still see itself as active and wrongly mark the agent disconnected.
            assignations = await self.backend.on_agent_connected(self.agent.pk, self.connection_id, session_id=self.session_id)
            if was_connected and register.force:
                await self.kick_others()
        else:
            # Non-executors (frontend/observer/caller) are NOT the singleton: no
            # displacement, no ``active_connection_id`` claim (that would corrupt the
            # executor's liveness on a shared Agent row), and no in-flight inquiries.
            assignations = await self.backend.on_observer_connected(self.agent.pk, self.connection_id, mode=self.mode.value)

        await self.send_to_agent_message(
            messages.Init(
                agent=str(self.agent.pk),
                inquiries=[messages.AssignInquiry(assignation=str(a.pk)) for a in assignations],
            )
        )

        # The redis per-agent task queue carries ToAgent executor commands (Assign,
        # Cancel, …) — only an executor should drain it. Heartbeat liveness runs for
        # every mode (a caller's death must be detectable to cascade-cancel its work).
        if self.executes_work:
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
        self.agent.last_seen = timezone.now()
        await self.agent.asave(update_fields=["connected", "last_seen"])

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
                    await self.queue.ack(agent_id, task)
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
            # Executor teardown drives the in-flight failure/grace cascade over EXECUTED work.
            if self.executes_work:
                await self.backend.on_agent_disconnected(self.agent.pk, self.connection_id)
            # Caller-death drives the cascade over ORIGINATED roots — independent of execution,
            # so it runs for every mode (the backend no-ops it for observers).
            await self.backend.on_caller_disconnected(
                self.agent.pk, self.connection_id, session_id=self.session_id, mode=self.mode.value
            )

        await self.queue.close()
