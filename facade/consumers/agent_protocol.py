"""Transport-agnostic agent protocol (the Humble Object).

All of the agent conversation logic lives here as a plain object with injected
dependencies — it knows nothing about Django Channels or WebSockets. ``send`` and
``close`` are callables wired by the adapter (``AgentConsumer``); ``backend`` and
``queue`` are ports; ``authenticator`` resolves a registration to an agent.

Because every collaborator is injected, the protocol/lifecycle/heartbeat
behaviour is unit-testable with fakes — no docker, no DB, no monkeypatching.

The conversation has two phases, split across two objects so the static types match
the runtime contract. :class:`AgentProtocol` is built at connect time and owns the
pre-register handshake (parse / validate / gate). On a successful ``Register`` it
constructs a :class:`RegisteredSession`, the post-register half, whose ``agent`` and
``capabilities`` are therefore non-Optional for its whole lifetime — no defensive
``self.agent`` guards scattered through dispatch/heartbeat/shutdown.
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

from facade import capabilities, codes, liveness, messages, models
from facade.capabilities import Capabilities
from facade.consumers.agent_queue import AgentQueue
from facade.message_router import UnknownAgentMessage, route_from_agent_message
from facade.persist_backend import persist_backend
from facade.ports import PersistBackend

logger = logging.getLogger(__name__)

SendCallable = Callable[[str], Awaitable[None]]
CloseCallable = Callable[[int], Awaitable[None]]
# A guarded send of an already-serialized frame (the outer protocol's lock-held ``_send``),
# and the typed message send built on top of it — both injected into a RegisteredSession so
# every outbound frame still funnels through the single outer send-lock.
SendTextCallable = Callable[[str], Awaitable[None]]
SendMessageCallable = Callable[[messages.ToAgentMessage], Awaitable[None]]
# The authenticator resolves a Register to the durable agent identity AND the
# capabilities granted by its token scopes (the two are decided together, from the
# same token, so the protocol never has to re-authenticate to learn capabilities).
Authenticator = Callable[[messages.Register], Awaitable[tuple["models.Agent", Capabilities]]]
# Wired by the adapter so the protocol can join the agent's connection group and
# displace other live connections — both are no-ops by default (unit tests).
RegisterConnectionCallable = Callable[[str], Awaitable[None]]
KickOthersCallable = Callable[[], Awaitable[None]]
# Wired by the adapter so the protocol can join the caller event group
# (``task_caller_{caller_id}``) and receive the events of work it originated.
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


class RegisteredSession:
    """The post-registration half of the agent conversation.

    Built by :class:`AgentProtocol.on_register` only once a ``Register`` has
    authenticated and passed every gate, so ``agent``/``capabilities`` are non-Optional
    for the object's whole lifetime. It owns dispatch of post-register frames, the
    executor task-queue drain, the heartbeat loop, and the disconnect cascade.

    Transport access is via the three callables injected by the outer protocol
    (``send_to_agent_message``/``_send``/``close``) rather than a back-reference, so the
    outbound send-lock stays singular on the outer object and there is no reference cycle.
    """

    def __init__(
        self,
        *,
        agent: "models.Agent",
        capabilities: Capabilities,
        mode: messages.AgentMode,
        executes_work: bool,
        session_id: Optional[str],
        caller_id: str,
        connection_id: str,
        backend: PersistBackend,
        queue: AgentQueue,
        send_to_agent_message: SendMessageCallable,
        send: SendTextCallable,
        close: CloseCallable,
        heartbeat_interval: float,
        heartbeat_timeout: float,
    ) -> None:
        self.agent = agent
        self.capabilities = capabilities
        self.mode = mode
        self.executes_work = executes_work
        self.session_id = session_id
        self.caller_id = caller_id
        self.connection_id = connection_id
        self.backend = backend
        self.queue = queue
        self.send_to_agent_message = send_to_agent_message
        self._send = send
        self.close = close
        self.heartbeat_interval = heartbeat_interval
        self.heartbeat_timeout = heartbeat_timeout

        self.heartbeat_future: Optional[asyncio.Future] = None
        self.listen_task: Optional[asyncio.Task] = None
        self.heartbeat_task: Optional[asyncio.Task] = None

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

    async def on_agent_heartbeat(self) -> None:
        """Record liveness and resolve the pending heartbeat future."""
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
        """Cancel loops and drive the disconnect cascade for this session."""
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

        # Executor teardown drives the in-flight failure/grace cascade over EXECUTED work.
        if self.executes_work:
            await self.backend.on_agent_disconnected(self.agent.pk, self.connection_id)
        # Caller-death drives the cascade over ORIGINATED roots — independent of execution,
        # so it runs for every mode (the backend no-ops it for observers).
        await self.backend.on_caller_disconnected(self.agent.pk, self.connection_id, session_id=self.session_id, mode=self.mode.value)


class AgentProtocol:
    """Drives the pre-register handshake over injected transport + ports.

    Built at connect time, before the agent is known. It parses/validates inbound
    frames, gates the ``Register``, and on success constructs the
    :class:`RegisteredSession` that owns the rest of the conversation. The single
    Optional is :attr:`session`, checked once at dispatch.
    """

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
        self.heartbeat_interval = heartbeat_interval if heartbeat_interval is not None else settings.AGENT_HEARTBEAT_INTERVAL
        self.heartbeat_timeout = heartbeat_timeout if heartbeat_timeout is not None else settings.AGENT_HEARTBEAT_RESPONSE_TIMEOUT

        # Built only on a successful Register; until then there is no agent identity.
        self.session: Optional[RegisteredSession] = None
        self.received_initial_payload = False
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
        if text_data is None:
            # A non-text (e.g. binary) frame — there is no JSON to parse.
            await self.close(codes.FROM_AGENT_MESSAGE_IS_NOT_VALID_JSON_CODE)
            return
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
            elif self.session is not None:
                await self.session.dispatch(payload.message)
            else:
                # received_initial_payload is set but no session exists — registration
                # was attempted and rejected (gate closed the socket). Nothing to dispatch.
                await self.close(codes.FROM_AGENT_MESSAGE_DOES_NOT_MATCH_SCHEMA_CODE)
        except Exception:
            logger.error("Unknown error handling agent message", exc_info=True)
            await self.close(codes.FROM_AGENT_MESSAGE_DOES_NOT_MATCH_SCHEMA_CODE)

    async def on_register(self, register: messages.Register) -> None:
        """Authenticate, authorize the requested mode, send ``Init`` and spawn loops.

        Gate order (each gate may close and return, leaving ``self.session`` None): authenticate →
        blocked → mode authorization → conflict/displacement (executors only) → build session +
        Init + loops.
        """
        agent, caps = await self.authenticator(register)
        mode = messages.AgentMode(register.mode)
        session_id = register.session_id
        executes_work = capabilities.mode_executes_work(mode)

        if agent.blocked:
            await self.close(codes.AGENT_IS_BLOCKED_CODE)
            return

        # Capabilities come from the token, never self-declaration: a participant may
        # only operate in a mode its scopes cover.
        if not capabilities.authorize_mode(caps, mode):
            await self.send_to_agent_message(messages.ProtocolError(error=f"Token is not authorized for mode {mode.value}."))
            await self.close(codes.MODE_NOT_AUTHORIZED_CODE)
            return

        # Join the caller event group for EVERY mode: even a pure executor assigns
        # *dependent* work and must receive its results back over this socket. Done
        # before Init so no originated-work event is missed.
        caller_id = await self.backend.get_or_create_caller_id(agent.pk)
        await self.register_caller(caller_id)

        # Caller reclaim: cancel any pending caller-death cascade for this session and adopt
        # the roots it originated (runs for every mode — any participant may originate work).
        await self.backend.on_caller_connected(agent.pk, self.connection_id, session_id)

        if executes_work:
            # The executor is a singleton: only one LIVE connection per agent. Reject a second
            # only when the incumbent is provably live (``connected`` AND a fresh heartbeat) and
            # ``force`` is not set. A STALE incumbent — ``connected`` stuck True but its heartbeat
            # expired (crashed/killed worker, half-open socket, in-memory timers lost on restart) —
            # is auto-displaced WITHOUT ``force``, so a genuinely-dead connection never wedges the
            # agent behind a ``--force`` reconnect. Liveness uses the same window as availability.
            was_connected = agent.connected
            incumbent_live = liveness.agent_is_live(agent.connected, agent.last_seen)
            if incumbent_live and not register.force:
                await self.send_to_agent_message(messages.ProtocolError(error="Another connection is already registered for this agent. Reconnect with force to take over."))
                await self.close(codes.AGENT_ALREADY_CONNECTED_CODE)
                return

            # Join the agent's connection group first (so we can later be kicked).
            await self.register_connection(agent.pk)

            # Claim ownership (sets ``active_connection_id`` to us) BEFORE displacing the
            # incumbent. Order matters: the displaced connection's disconnect handler is
            # guarded on ``active_connection_id`` — if we kicked before claiming, it could
            # still see itself as active and wrongly mark the agent disconnected.
            tasks = await self.backend.on_agent_connected(agent.pk, self.connection_id, session_id=session_id)
            # Displace any prior connection whenever there was one — a forced takeover of a live
            # incumbent OR an auto-takeover of a stale one whose socket may still be half-open on
            # another worker. ``kick_others`` is keyed on our ``connection_id`` (never closes us)
            # and is a harmless no-op when the group is empty (the dead-worker case).
            if was_connected:
                await self.kick_others()
        else:
            # Non-executors (frontend/observer/caller) are NOT the singleton: no
            # displacement, no ``active_connection_id`` claim (that would corrupt the
            # executor's liveness on a shared Agent row), and no in-flight inquiries.
            tasks = await self.backend.on_observer_connected(agent.pk, self.connection_id, mode=mode.value)

        # Registration succeeded: everything from here is the post-register half.
        self.session = RegisteredSession(
            agent=agent,
            capabilities=caps,
            mode=mode,
            executes_work=executes_work,
            session_id=session_id,
            caller_id=caller_id,
            connection_id=self.connection_id,
            backend=self.backend,
            queue=self.queue,
            send_to_agent_message=self.send_to_agent_message,
            send=self._send,
            close=self.close,
            heartbeat_interval=self.heartbeat_interval,
            heartbeat_timeout=self.heartbeat_timeout,
        )

        await self.send_to_agent_message(
            messages.Init(
                agent=str(agent.pk),
                inquiries=[messages.AssignInquiry(task=str(a.pk)) for a in tasks],
            )
        )

        # The redis per-agent task queue carries ToAgent executor commands (Assign,
        # Cancel, …) — only an executor should drain it. Heartbeat liveness runs for
        # every mode (a caller's death must be detectable to cascade-cancel its work).
        if executes_work:
            self.session.listen_task = asyncio.create_task(self.session.listen_for_tasks(agent.pk))
        self.session.heartbeat_task = asyncio.create_task(self.session.heartbeat(agent.pk))

    async def shutdown(self) -> None:
        """Tear down the registered session (if any) and release the queue."""
        if self.session is not None:
            await self.session.shutdown()
        await self.queue.close()
