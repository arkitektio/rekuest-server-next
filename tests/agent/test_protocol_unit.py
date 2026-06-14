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

import pytest

from facade import messages
from facade.codes import (
    AGENT_ALREADY_CONNECTED_CODE,
    AGENT_IS_BLOCKED_CODE,
    FROM_AGENT_MESSAGE_DOES_NOT_MATCH_SCHEMA_CODE,
    FROM_AGENT_MESSAGE_IS_NOT_VALID_JSON_CODE,
    HEARTBEAT_NOT_RESPONDED_CODE,
)
from facade.consumers.agent_protocol import AgentProtocol
from facade.consumers.agent_queue import InMemoryAgentQueue

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

    def __init__(self, assignations=None):
        self.assignations = assignations or []
        self.calls = []

    async def on_agent_connected(self, agent_id, connection_id=None):
        self.calls.append(("connected", agent_id))
        return self.assignations

    async def on_agent_disconnected(self, agent_id, connection_id=None):
        self.calls.append(("disconnected", agent_id))

    async def on_agent_log(self, agent_id, message):
        self.calls.append(("log", agent_id, message))


def make_protocol(agent=None, backend=None, queue=None, heartbeat_interval=10.0, heartbeat_timeout=5.0, kick_others=None, register_connection=None):
    """Build an ``AgentProtocol`` wired to list-collecting transport callables."""
    sent = []
    closed = []

    async def send(text):
        sent.append(text)

    async def close(code):
        closed.append(code)

    agent = agent if agent is not None else FakeAgent()

    async def authenticator(register):
        return agent

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


def _register_frame(instance_id="unit-agent", token=TEST_TOKEN, force=False):
    return messages.Register(token=token, force=force).model_dump_json()


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
        # No background loops were spawned for a rejected registration.
        assert protocol.listen_task is None
        assert protocol.heartbeat_task is None

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

    async def test_unhandled_message_closes(self):
        protocol, sent, closed, _ = make_protocol()
        await protocol.receive(_register_frame())
        await protocol.receive(messages.LockEvent(key="lock-1", assignation=str(uuid.uuid4())).model_dump_json())
        assert FROM_AGENT_MESSAGE_DOES_NOT_MATCH_SCHEMA_CODE in closed
        await protocol.shutdown()

    async def test_log_event_routes_to_backend(self):
        backend = FakeBackend()
        protocol, sent, closed, _ = make_protocol(backend=backend)
        await protocol.receive(_register_frame())
        await protocol.receive(
            messages.LogEvent(assignation=str(uuid.uuid4()), message="hello", level="INFO").model_dump_json()
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
        await protocol.on_agent_heartbeat()

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
            return FakeAgent()

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
        protocol.agent = agent  # simulate post-registration state
        future = asyncio.get_event_loop().create_future()
        protocol.heartbeat_future = future

        task = asyncio.create_task(protocol.on_agent_heartbeat())
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
        first_listen = protocol.listen_task
        first_heartbeat = protocol.heartbeat_task

        await protocol.receive(_register_frame())

        assert FROM_AGENT_MESSAGE_DOES_NOT_MATCH_SCHEMA_CODE in closed
        # The task handles are untouched — no new pair was spawned.
        assert protocol.listen_task is first_listen
        assert protocol.heartbeat_task is first_heartbeat

        await protocol.shutdown()
        # The original pair is the one shutdown cancels — nothing left orphaned.
        assert first_listen.cancelled() or first_listen.done()
        assert first_heartbeat.cancelled() or first_heartbeat.done()
