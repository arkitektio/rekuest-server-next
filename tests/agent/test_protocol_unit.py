"""AgentProtocol unit tests.

These drive the transport-agnostic ``AgentProtocol`` directly with in-memory fakes
(no Channels, no DB, no redis, no docker, no monkeypatch). They cover the
protocol/lifecycle/routing/heartbeat decisions that would otherwise need the full
stack. Run them with ``pytest tests/agent/test_protocol_unit.py`` with the stack
down to confirm they have no external dependency.

The fakes (``FakeAgent`` / ``FakeBackend`` / ``make_protocol``) and the
``_wait_for`` / ``_register_frame`` helpers are unit-only and intentionally local
to this module.
"""

import asyncio
import json
import uuid
from types import SimpleNamespace

import pytest

from facade import messages
from facade.codes import (
    AGENT_ALREADY_CONNECTED_CODE,
    AGENT_IS_BLOCKED_CODE,
    FROM_AGENT_MESSAGE_DOES_NOT_MATCH_SCHEMA_CODE,
    FROM_AGENT_MESSAGE_IS_NOT_VALID_JSON_CODE,
    HEARTBEAT_NOT_RESPONDED_CODE,
)
from facade.capabilities import Capabilities
from facade.consumers.agent_protocol import AgentProtocol, RegisteredSession
from facade.consumers.agent_queue import InMemoryAgentQueue

# Full executor-and-caller; mirrors the rollout default (enforcement off).
FULL_CAPABILITIES = Capabilities(executes_work=True, can_assign_root=True)

from tests.factories import TEST_TOKEN


class FakeAgent:
    """Stand-in for the ``Agent`` model the authenticator would return."""

    def __init__(self, pk="agent-1", instance_id="unit-agent", blocked=False, connected=False):
        self.pk = pk
        self.instance_id = instance_id
        self.blocked = blocked
        self.connected = connected
        self.last_seen = None
        self.active_connection_id = None
        self.saves = 0

    async def asave(self, **kwargs):
        self.saves += 1


class FakeBackend:
    """Records which persist-backend hook the protocol routed each message to."""

    def __init__(self, tasks=None, caller_assign_error=None):
        self.tasks = tasks or []
        self.calls = []
        # When set, on_caller_assign raises it (to exercise the nack path).
        self.caller_assign_error = caller_assign_error

    async def on_agent_done(self, agent_id, message):
        self.calls.append(("done", agent_id, message))

    async def on_caller_assign(self, agent_id, message, can_assign_root, connection_id=None, session_id=None):
        self.calls.append(("caller_assign", agent_id, message, can_assign_root))
        if self.caller_assign_error is not None:
            raise self.caller_assign_error
        return SimpleNamespace(pk="new-ass-1"), True  # stands in for the created Task

    async def on_caller_cancel(self, agent_id, message, *, connection_id=None, session_id=None):
        self.calls.append(("caller_cancel", agent_id, message))
        if self.caller_assign_error is not None:
            raise self.caller_assign_error
        return SimpleNamespace(pk="ctrl-ass-1")

    async def on_agent_connected(self, agent_id, connection_id=None, session_id=None):
        self.calls.append(("connected", agent_id))
        return self.tasks

    async def get_or_create_caller_id(self, agent_id):
        self.calls.append(("caller_id", agent_id))
        return f"caller-{agent_id}"

    async def on_agent_disconnected(self, agent_id, connection_id=None):
        self.calls.append(("disconnected", agent_id))

    async def on_observer_connected(self, agent_id, connection_id=None, mode=None):
        self.calls.append(("observer_connected", agent_id, mode))
        return self.tasks

    async def on_caller_connected(self, agent_id, connection_id=None, session_id=None):
        self.calls.append(("caller_connected", agent_id))

    async def on_caller_disconnected(self, agent_id, connection_id=None, session_id=None, mode=None):
        self.calls.append(("caller_disconnected", agent_id, mode))

    async def on_agent_log(self, agent_id, message):
        self.calls.append(("log", agent_id, message))


def make_protocol(agent=None, backend=None, queue=None, heartbeat_interval=10.0, heartbeat_timeout=5.0, kick_others=None, register_connection=None, capabilities=FULL_CAPABILITIES):
    """Build an ``AgentProtocol`` wired to list-collecting transport callables."""
    sent = []
    closed = []

    async def send(text):
        sent.append(text)

    async def close(code):
        closed.append(code)

    agent = agent if agent is not None else FakeAgent()

    async def authenticator(register):
        return agent, capabilities

    kwargs = {}
    if kick_others is not None:
        kwargs["kick_others"] = kick_others
    if register_connection is not None:
        kwargs["register_connection"] = register_connection

    protocol = AgentProtocol(
        send=send,
        close=close,
        queue=queue if queue is not None else InMemoryAgentQueue(),
        backend=backend if backend is not None else FakeBackend(),
        authenticator=authenticator,
        heartbeat_interval=heartbeat_interval,
        heartbeat_timeout=heartbeat_timeout,
        **kwargs,
    )
    return protocol, sent, closed, agent


async def _wait_for(predicate, timeout=2.0, interval=0.01):
    """Poll ``predicate`` until true or ``timeout`` elapses; return its truthiness."""
    waited = 0.0
    while waited < timeout:
        if predicate():
            return True
        await asyncio.sleep(interval)
        waited += interval
    return predicate()


def _register_frame(instance_id="unit-agent", token=TEST_TOKEN, force=False, mode=messages.AgentMode.EXECUTOR, session_id=None):
    return messages.Register(token=token, force=force, mode=mode, session_id=session_id).model_dump_json()


@pytest.mark.asyncio
class TestAgentProtocolUnit:
    async def test_invalid_json_closes(self):
        protocol, sent, closed, _ = make_protocol()
        await protocol.receive("this is not json")
        assert closed == [FROM_AGENT_MESSAGE_IS_NOT_VALID_JSON_CODE]
        assert sent == []

    async def test_first_message_must_be_register(self):
        protocol, sent, closed, _ = make_protocol()
        await protocol.receive(messages.HeartbeatEvent().model_dump_json())
        assert closed == [FROM_AGENT_MESSAGE_DOES_NOT_MATCH_SCHEMA_CODE]

    async def test_schema_mismatch_sends_protocol_error_then_closes(self):
        protocol, sent, closed, _ = make_protocol()
        await protocol.receive('{"type": "TOTALLY_UNKNOWN"}')
        assert json.loads(sent[0])["type"] == messages.ToAgentMessageType.PROTOCOL_ERROR.value
        assert closed == [FROM_AGENT_MESSAGE_DOES_NOT_MATCH_SCHEMA_CODE]

    async def test_register_sends_init(self):
        protocol, sent, closed, agent = make_protocol()
        await protocol.receive(_register_frame())

        init = json.loads(sent[0])
        assert init["type"] == messages.ToAgentMessageType.INIT.value
        assert init["agent"] == str(agent.pk)
        assert init["inquiries"] == []
        assert closed == []
        await protocol.shutdown()

    async def test_blocked_agent_closes_without_init(self):
        protocol, sent, closed, _ = make_protocol(agent=FakeAgent(blocked=True))
        await protocol.receive(_register_frame())
        assert closed == [AGENT_IS_BLOCKED_CODE]
        assert sent == []

    async def test_register_rejected_when_already_connected_without_force(self):
        # An already-connected agent + no force -> ProtocolError then close 4004,
        # and crucially NO Init (the incumbent connection keeps the agent).
        kicked = []

        async def kick_others():
            kicked.append(True)

        protocol, sent, closed, _ = make_protocol(agent=FakeAgent(connected=True), kick_others=kick_others)
        await protocol.receive(_register_frame(force=False))

        assert json.loads(sent[0])["type"] == messages.ToAgentMessageType.PROTOCOL_ERROR.value
        assert closed == [AGENT_ALREADY_CONNECTED_CODE]
        assert kicked == []  # nobody is displaced on a plain rejection
        # No session (and thus no background loops) for a rejected registration.
        assert protocol.session is None

    async def test_force_register_kicks_incumbent_when_connected(self):
        # An already-connected agent + force -> displace the incumbent and proceed
        # to a normal Init.
        kicked = []

        async def kick_others():
            kicked.append(True)

        protocol, sent, closed, agent = make_protocol(agent=FakeAgent(connected=True), kick_others=kick_others)
        await protocol.receive(_register_frame(force=True))

        assert kicked == [True]
        assert json.loads(sent[0])["type"] == messages.ToAgentMessageType.INIT.value
        assert closed == []
        await protocol.shutdown()

    async def test_force_register_does_not_kick_when_not_connected(self):
        # force is a no-op when there is no incumbent: nobody gets kicked.
        kicked = []

        async def kick_others():
            kicked.append(True)

        protocol, sent, closed, _ = make_protocol(agent=FakeAgent(connected=False), kick_others=kick_others)
        await protocol.receive(_register_frame(force=True))

        assert kicked == []
        assert json.loads(sent[0])["type"] == messages.ToAgentMessageType.INIT.value
        await protocol.shutdown()

    # ----------------------------------------------------------------------- #
    # Capability / mode gating (the single-protocol, capability-bit model).
    # ----------------------------------------------------------------------- #
    async def test_mode_exceeding_capabilities_is_rejected(self):
        # A token that only grants executes_work may not register as CALLER (which
        # requires can_assign_root). Protocol error + MODE_NOT_AUTHORIZED, no Init.
        from facade.codes import MODE_NOT_AUTHORIZED_CODE

        exec_only = Capabilities(executes_work=True, can_assign_root=False)
        protocol, sent, closed, _ = make_protocol(capabilities=exec_only)
        await protocol.receive(_register_frame(mode=messages.AgentMode.CALLER))

        assert json.loads(sent[0])["type"] == messages.ToAgentMessageType.PROTOCOL_ERROR.value
        assert closed == [MODE_NOT_AUTHORIZED_CODE]
        assert protocol.session is None

    async def test_caller_mode_does_not_displace_and_skips_executor_queue(self):
        # A non-executor (CALLER) is NOT the singleton: even with an already-connected
        # agent and no force it is admitted (no AGENT_ALREADY_CONNECTED), gets an Init,
        # does NOT drain the executor task queue, but DOES run a heartbeat loop.
        backend = FakeBackend()
        kicked = []

        async def kick_others():
            kicked.append(True)

        protocol, sent, closed, agent = make_protocol(agent=FakeAgent(connected=True), backend=backend, kick_others=kick_others)
        await protocol.receive(_register_frame(mode=messages.AgentMode.CALLER, force=False))

        assert json.loads(sent[0])["type"] == messages.ToAgentMessageType.INIT.value
        assert closed == []
        assert kicked == []
        assert ("observer_connected", agent.pk, messages.AgentMode.CALLER.value) in backend.calls
        assert protocol.session.listen_task is None  # never drains executor commands
        assert protocol.session.heartbeat_task is not None  # liveness still tracked
        await protocol.shutdown()
        assert ("caller_disconnected", agent.pk, messages.AgentMode.CALLER.value) in backend.calls

    async def test_executor_threads_session_id_to_backend_connect(self):
        recorded = {}

        class RecordingBackend(FakeBackend):
            async def on_agent_connected(self, agent_id, connection_id=None, session_id=None):
                recorded["session_id"] = session_id
                return self.tasks

        protocol, sent, closed, _ = make_protocol(backend=RecordingBackend())
        await protocol.receive(_register_frame(mode=messages.AgentMode.EXECUTOR, session_id="proc-xyz"))
        assert recorded["session_id"] == "proc-xyz"
        await protocol.shutdown()

    async def test_caller_assign_routes_and_acks(self):
        backend = FakeBackend()
        protocol, sent, closed, agent = make_protocol(backend=backend)
        await protocol.receive(_register_frame())
        sent.clear()

        req = messages.AssignRequest(reference="ref-1", action="act-1", args={"x": 1})
        await protocol.receive(req.model_dump_json())

        # routed to the backend with the connection's can_assign_root capability
        ca = next(c for c in backend.calls if c[0] == "caller_assign")
        assert ca[3] is True  # FULL_CAPABILITIES.can_assign_root
        # and a AssignResponse ack echoing the request id + reference
        result = json.loads(sent[-1])
        assert result["type"] == messages.ToAgentMessageType.ASSIGN_RESPONSE.value
        assert result["request"] == req.id and result["reference"] == "ref-1"
        assert result["task"] == "new-ass-1" and result["created"] is True
        assert closed == []
        await protocol.shutdown()

    async def test_caller_assign_failure_nacks_without_closing(self):
        # A backend error must nack the caller, NOT close the socket (which would kill all
        # the agent's other work).
        backend = FakeBackend(caller_assign_error=PermissionError("missing can_assign_root"))
        protocol, sent, closed, _ = make_protocol(backend=backend)
        await protocol.receive(_register_frame())
        sent.clear()

        await protocol.receive(messages.AssignRequest(reference="ref-2", args={}).model_dump_json())

        result = json.loads(sent[-1])
        assert result["type"] == messages.ToAgentMessageType.ASSIGN_RESPONSE.value
        assert result["task"] is None and result["created"] is False
        assert "missing can_assign_root" in result["error"]
        assert closed == []  # crucially, the connection stays open
        await protocol.shutdown()

    async def test_terminal_event_is_acked(self):
        backend = FakeBackend()
        protocol, sent, closed, _ = make_protocol(backend=backend)
        await protocol.receive(_register_frame())
        sent.clear()

        done = messages.Completed(task="ass-9", seq=7)
        await protocol.receive(done.model_dump_json())

        ack = json.loads(sent[-1])
        assert ack["type"] == messages.ToAgentMessageType.EVENT_ACK.value
        assert ack["event"] == done.id and ack["task"] == "ass-9" and ack["seq"] == 7
        await protocol.shutdown()

    async def test_caller_control_routes_and_acks(self):
        backend = FakeBackend()
        protocol, sent, closed, _ = make_protocol(backend=backend)
        await protocol.receive(_register_frame())
        sent.clear()

        req = messages.CancelRequest(task="ass-7", auto_interrupt=5)
        await protocol.receive(req.model_dump_json())

        assert any(c[0] == "caller_cancel" for c in backend.calls)
        result = json.loads(sent[-1])
        assert result["type"] == messages.ToAgentMessageType.CONTROL_RESPONSE.value
        assert result["request"] == req.id and result["accepted"] is True
        assert closed == []
        await protocol.shutdown()

    async def test_caller_control_failure_nacks_without_closing(self):
        backend = FakeBackend(caller_assign_error=PermissionError("not the caller"))
        protocol, sent, closed, _ = make_protocol(backend=backend)
        await protocol.receive(_register_frame())
        sent.clear()

        await protocol.receive(messages.CancelRequest(task="ass-x").model_dump_json())

        result = json.loads(sent[-1])
        assert result["type"] == messages.ToAgentMessageType.CONTROL_RESPONSE.value
        assert result["accepted"] is False and "not the caller" in result["error"]
        assert closed == []  # a bad control request never tears down the socket
        await protocol.shutdown()

    async def test_unhandled_message_closes(self):
        protocol, sent, closed, _ = make_protocol()
        await protocol.receive(_register_frame())
        # A second Register (after the handshake) has no router case → closes the socket.
        await protocol.receive(_register_frame())
        assert FROM_AGENT_MESSAGE_DOES_NOT_MATCH_SCHEMA_CODE in closed
        await protocol.shutdown()

    async def test_log_event_routes_to_backend(self):
        backend = FakeBackend()
        protocol, sent, closed, _ = make_protocol(backend=backend)
        await protocol.receive(_register_frame())
        await protocol.receive(
            messages.Log(task=str(uuid.uuid4()), message="hello", level="INFO").model_dump_json()
        )
        assert any(call[0] == "log" for call in backend.calls)
        await protocol.shutdown()

    async def test_shutdown_marks_agent_disconnected(self):
        backend = FakeBackend()
        protocol, sent, closed, agent = make_protocol(backend=backend)
        await protocol.receive(_register_frame())
        await protocol.shutdown()
        assert ("disconnected", agent.pk) in backend.calls

    async def test_queued_message_is_relayed_to_agent(self):
        queue = InMemoryAgentQueue()
        protocol, sent, closed, agent = make_protocol(queue=queue)
        await protocol.receive(_register_frame())

        queue.push(str(agent.pk), '{"hello": 1}')

        assert await _wait_for(lambda: any('"hello"' in s for s in sent))
        await protocol.shutdown()

    async def test_heartbeat_answer_keeps_protocol_open(self):
        protocol, sent, closed, _ = make_protocol(heartbeat_interval=0.05, heartbeat_timeout=0.3)
        await protocol.receive(_register_frame())

        def _heartbeats():
            return [s for s in sent if json.loads(s)["type"] == messages.ToAgentMessageType.HEARTBEAT.value]

        assert await _wait_for(lambda: len(_heartbeats()) >= 1)
        await protocol.session.on_agent_heartbeat()

        # Give the loop time to time out if the answer had not been accepted.
        await asyncio.sleep(0.2)
        assert HEARTBEAT_NOT_RESPONDED_CODE not in closed
        await protocol.shutdown()

    async def test_unanswered_heartbeat_closes(self):
        protocol, sent, closed, _ = make_protocol(heartbeat_interval=0.05, heartbeat_timeout=0.1)
        await protocol.receive(_register_frame())

        assert await _wait_for(lambda: HEARTBEAT_NOT_RESPONDED_CODE in closed)
        await protocol.shutdown()

    # ----------------------------------------------------------------------- #
    # Race-condition isolation (R1-R4). Each test fails if its fix is reverted.
    # ----------------------------------------------------------------------- #
    async def test_concurrent_sends_are_serialized(self):
        # R1: every outbound frame funnels through one lock. A send that yields
        # mid-flight must never have a second send overlapping it. Without the
        # lock, the gathered sends would all enter and ``max`` would reach 10.
        state = {"now": 0, "max": 0}

        async def send(text):
            state["now"] += 1
            state["max"] = max(state["max"], state["now"])
            await asyncio.sleep(0)  # yield: an unguarded peer could interleave here
            state["now"] -= 1

        async def close(code):
            pass

        async def authenticator(register):
            return FakeAgent(), FULL_CAPABILITIES

        protocol = AgentProtocol(
            send=send,
            close=close,
            queue=InMemoryAgentQueue(),
            backend=FakeBackend(),
            authenticator=authenticator,
        )

        # All concurrent producers (heartbeat ping, listen relay, receive-path
        # sends) reach the wire through ``send_to_agent_message`` / ``_send``.
        await asyncio.gather(*[protocol.send_to_agent_message(messages.Heartbeat()) for _ in range(10)])

        assert state["max"] == 1

    async def test_heartbeat_answer_resolved_before_persist(self):
        # R2: on_agent_heartbeat must resolve the handshake future BEFORE awaiting
        # the (slow) DB persist. A blocking asave must not delay resolution.
        agent = FakeAgent()
        release = asyncio.Event()

        async def blocking_asave(**kwargs):
            await release.wait()

        agent.asave = blocking_asave

        protocol, sent, closed, _ = make_protocol(agent=agent)
        # Build the post-registration session directly to exercise its heartbeat handling.
        session = RegisteredSession(
            agent=agent,
            capabilities=FULL_CAPABILITIES,
            mode=messages.AgentMode.EXECUTOR,
            executes_work=True,
            session_id=None,
            caller_id="caller",
            connection_id=protocol.connection_id,
            backend=protocol.backend,
            queue=protocol.queue,
            send_to_agent_message=protocol.send_to_agent_message,
            send=protocol._send,
            close=protocol.close,
            heartbeat_interval=protocol.heartbeat_interval,
            heartbeat_timeout=protocol.heartbeat_timeout,
        )
        protocol.session = session
        future = asyncio.get_event_loop().create_future()
        session.heartbeat_future = future

        task = asyncio.create_task(session.on_agent_heartbeat())
        try:
            # The future is resolved even though asave is still blocked.
            assert await _wait_for(lambda: future.done())
            assert not task.done()  # still parked in asave
        finally:
            release.set()
            await task

    async def test_heartbeat_loop_stops_after_timeout_close(self):
        # R3: after an unanswered timeout the loop must terminate, not keep
        # pinging a closed socket.
        protocol, sent, closed, _ = make_protocol(heartbeat_interval=0.05, heartbeat_timeout=0.1)
        await protocol.receive(_register_frame())

        def _pings():
            return [s for s in sent if json.loads(s)["type"] == messages.ToAgentMessageType.HEARTBEAT.value]

        assert await _wait_for(lambda: HEARTBEAT_NOT_RESPONDED_CODE in closed)
        pings_at_close = len(_pings())

        # Several more intervals elapse; a live loop would emit more pings/closes.
        await asyncio.sleep(0.3)
        assert len(_pings()) == pings_at_close == 1
        assert closed.count(HEARTBEAT_NOT_RESPONDED_CODE) == 1
        await protocol.shutdown()

    async def test_second_register_is_rejected_without_respawning_tasks(self):
        # R4: a duplicate Register must not re-run on_register (which would orphan
        # the first listen/heartbeat task pair). It closes instead.
        protocol, sent, closed, _ = make_protocol()
        await protocol.receive(_register_frame())
        session = protocol.session
        first_listen = session.listen_task
        first_heartbeat = session.heartbeat_task

        await protocol.receive(_register_frame())

        assert FROM_AGENT_MESSAGE_DOES_NOT_MATCH_SCHEMA_CODE in closed
        # The session and its task handles are untouched — no new pair was spawned.
        assert protocol.session is session
        assert session.listen_task is first_listen
        assert session.heartbeat_task is first_heartbeat

        await protocol.shutdown()
        # The original pair is the one shutdown cancels — nothing left orphaned.
        assert first_listen.cancelled() or first_listen.done()
        assert first_heartbeat.cancelled() or first_heartbeat.done()
