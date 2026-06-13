"""End-to-end tests for the agent WebSocket protocol.

These drive the real ``AgentConsumer`` (``facade/consumers/async_consumer.py``)
through Django Channels' ``WebsocketCommunicator`` against real Postgres and real
Redis (both started by the ``backend_stack`` dokker fixture in ``conftest.py``).

Two facts shape these tests:

* The agent queue reads its redis endpoint from ``settings.AGENT_REDIS_HOST`` /
  ``AGENT_REDIS_PORT`` (``settings_test`` points them at ``localhost:6666``); the
  ``agent_ws_redis`` fixture just flushes that redis between tests.
* ``default_authenticator`` only *finds* an existing agent — its
  ``aget_or_create`` create-branch omits the required ``app``/``release``/``device``
  columns, so brand-new agents cannot be created over the socket. In normal
  operation the agent is created first via the ``ensureAgent`` GraphQL mutation and
  then connects. ``seed_agent`` reproduces that by pre-creating the agent against the
  exact identity the consumer derives from the token, so registration takes the
  get-branch.

Tiers:
  * ``TestAgentWalkingSkeleton`` / ``TestAgentProtocol`` — connect/auth/close-codes,
    register -> Init, blocked agent, disconnect (full stack).
  * ``TestAgentEvents`` — event persistence (Log/Progress/Yield/Done/Cancelled/Error/
    Critical) and state events (StatePatch/StateSnapshot/SessionInit) (full stack).
  * ``TestAgentDelivery`` — redis round-trip (broadcast -> agent) (full stack).
  * ``TestAgentProtocolUnit`` — protocol/lifecycle/routing/heartbeat driven against
    ``AgentProtocol`` with in-memory fakes; NO docker/DB/redis/monkeypatch.

Coverage gap (by design, not omission): the protocol's ``dispatch`` has no handler
for several valid ``FromAgentMessage`` types — ``LockEvent``, ``UnlockEvent``,
``PausedEvent``, ``ResumedEvent``, ``SteppedEvent``, ``InterruptedEvent`` — which
all fall through to ``case _:`` and close the socket (3003). That fall-through is
covered generically by ``test_valid_but_unhandled_message_closes_socket`` (full
stack) and ``TestAgentProtocolUnit.test_unhandled_message_closes`` (unit); the
individual semantics are untested because the protocol implements none.
"""

import asyncio
import json
import uuid

import pytest
from asgiref.sync import sync_to_async

from authentikate.expand import (
    aexpand_client_from_token,
    aexpand_organization_from_token,
    aexpand_user_from_token,
)
from authentikate.models import App, Client, Device, Organization, Release, User
from authentikate.utils import authenticate_token_or_none
from facade import enums, messages
from facade.codes import (
    AGENT_IS_BLOCKED_CODE,
    FROM_AGENT_MESSAGE_DOES_NOT_MATCH_SCHEMA_CODE,
    FROM_AGENT_MESSAGE_IS_NOT_VALID_JSON_CODE,
    HEARTBEAT_NOT_RESPONDED_CODE,
)
from facade.consumers.agent_protocol import AgentProtocol
from facade.consumers.agent_queue import InMemoryAgentQueue
from facade.consumers.async_consumer import AgentConsumer
from facade.models import (
    Action,
    Agent,
    Assignation,
    AssignationEvent,
    Implementation,
    Patch,
    Registry,
    Snapshot,
    State,
    StateDefinition,
    Waiter,
)

RECEIVE_TIMEOUT = 5
TEST_TOKEN = "test"


# --------------------------------------------------------------------------- #
# Protocol helpers
# --------------------------------------------------------------------------- #
async def register(communicator, instance_id="test-agent", token=TEST_TOKEN):
    """Send a ``Register`` and return the parsed ``Init`` response payload."""
    await communicator.send_to(text_data=messages.Register(instance_id=instance_id, token=token).model_dump_json())
    return await communicator.receive_json_from(timeout=RECEIVE_TIMEOUT)


async def send_message(communicator, message):
    """Serialize a pydantic message and send it over the socket."""
    await communicator.send_to(text_data=message.model_dump_json())


async def _seed_agent(instance_id, token=TEST_TOKEN, blocked=False):
    """Pre-create the agent the consumer will look up for ``token`` + ``instance_id``.

    Uses the same authentikate expansion the consumer uses, so the derived
    Registry matches and ``on_register`` finds (rather than creates) the agent.
    """
    decoded = await authenticate_token_or_none(token)
    user = await aexpand_user_from_token(decoded)
    client = await aexpand_client_from_token(decoded)
    organization = await aexpand_organization_from_token(decoded)
    registry, _ = await Registry.objects.aget_or_create(client=client, user=user, organization=organization)

    app, _ = await App.objects.aget_or_create(identifier="ws-test-app")
    release, _ = await Release.objects.aget_or_create(app=app, version="1.0.0")
    device, _ = await Device.objects.aget_or_create(device_id="ws-test-device")

    agent, _ = await Agent.objects.aupdate_or_create(
        registry=registry,
        instance_id=instance_id,
        defaults=dict(
            app=app, release=release, device=device, user=user,
            organization=organization, hash=f"{instance_id}-hash", blocked=blocked,
        ),
    )
    return agent


async def connect_and_register(agent_ws, instance_id, **seed_kwargs):
    """Seed the agent, connect, register, and return ``(communicator, init)``."""
    await _seed_agent(instance_id, **seed_kwargs)
    communicator = await agent_ws()
    init = await register(communicator, instance_id=instance_id)
    return communicator, init


# --------------------------------------------------------------------------- #
# Object-graph builders (run synchronously, wrapped via sync_to_async)
# --------------------------------------------------------------------------- #
def _build_assignation(prefix):
    """Create a standalone Action -> Implementation -> Assignation graph.

    The persist backend looks assignations up by id (not by the registered agent),
    so this graph is independent of the agent that streams the events.
    """
    user = User.objects.create(username=f"{prefix}-user", password="x", sub=f"{prefix}-sub")
    client = Client.objects.create(client_id=f"{prefix}-client")
    org = Organization.objects.create(slug=f"{prefix}-org")
    registry = Registry.objects.create(client=client, user=user, organization=org)

    app = App.objects.create(identifier=f"{prefix}-app")
    release = Release.objects.create(app=app, version="1.0.0")
    device = Device.objects.create(device_id=f"{prefix}-device")
    agent = Agent.objects.create(
        app=app, hash=f"{prefix}-hash", release=release, device=device,
        user=user, registry=registry, organization=org, instance_id=f"{prefix}-inst",
    )

    action = Action.objects.create(
        app=app, key=f"{prefix}-key", version="1.0.0", name=f"{prefix} action",
        description=f"{prefix} description", hash=f"{prefix}-action-hash", organization=org,
    )
    implementation = Implementation.objects.create(
        release=release, interface=f"{prefix}-iface", action=action, agent=agent, dynamic=False,
    )
    waiter = Waiter.objects.create(registry=registry, instance_id=f"{prefix}-waiter")

    return Assignation.objects.create(
        waiter=waiter,
        action=action,
        agent=agent,
        implementation=implementation,
        latest_event_kind=enums.AssignationEventKind.ASSIGN,
        latest_instruct_kind=enums.AssignationInstructChoices.ASSIGN,
    )


def _build_state_for_agent(agent_pk, interface, prefix):
    """Create a State (and its definition) attached to an existing agent."""
    definition = StateDefinition.objects.create(
        name=f"{prefix} state", hash=f"{prefix}-state-hash", ports=[], description=f"{prefix} state def",
    )
    return State.objects.create(definition=definition, interface=interface, agent_id=agent_pk, value={})


build_assignation = sync_to_async(_build_assignation)
build_state_for_agent = sync_to_async(_build_state_for_agent)


# --------------------------------------------------------------------------- #
# Tier 1: walking skeleton (must be green inside the full suite before the rest)
# --------------------------------------------------------------------------- #
@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
class TestAgentWalkingSkeleton:
    async def test_register_returns_init_for_seeded_agent(self, agent_ws):
        agent = await _seed_agent("skeleton-agent")

        communicator = await agent_ws()
        init = await register(communicator, instance_id="skeleton-agent")

        assert init["type"] == messages.ToAgentMessageType.INIT.value
        assert init["instance_id"] == "skeleton-agent"
        assert init["agent"] == str(agent.pk)


# --------------------------------------------------------------------------- #
# Tier 1: protocol / lifecycle
# --------------------------------------------------------------------------- #
@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
class TestAgentProtocol:
    async def test_connection_is_accepted(self, agent_ws):
        # The fixture asserts connection success; reaching here proves accept().
        await agent_ws()

    async def test_first_message_must_be_register(self, agent_ws):
        communicator = await agent_ws()
        # A valid-but-non-register message as the very first frame -> close 3003.
        await send_message(communicator, messages.HeartbeatEvent())
        output = await communicator.receive_output(timeout=RECEIVE_TIMEOUT)
        assert output["type"] == "websocket.close"
        assert output["code"] == FROM_AGENT_MESSAGE_DOES_NOT_MATCH_SCHEMA_CODE

    async def test_invalid_json_closes_socket(self, agent_ws):
        communicator = await agent_ws()
        await communicator.send_to(text_data="this is not json")
        output = await communicator.receive_output(timeout=RECEIVE_TIMEOUT)
        assert output["type"] == "websocket.close"
        assert output["code"] == FROM_AGENT_MESSAGE_IS_NOT_VALID_JSON_CODE

    async def test_schema_mismatch_sends_protocol_error_then_closes(self, agent_ws):
        communicator = await agent_ws()
        await communicator.send_to(text_data='{"type": "TOTALLY_UNKNOWN"}')

        error = await communicator.receive_json_from(timeout=RECEIVE_TIMEOUT)
        assert error["type"] == messages.ToAgentMessageType.PROTOCOL_ERROR.value
        assert error["error"]

        output = await communicator.receive_output(timeout=RECEIVE_TIMEOUT)
        assert output["type"] == "websocket.close"
        assert output["code"] == FROM_AGENT_MESSAGE_DOES_NOT_MATCH_SCHEMA_CODE

    async def test_successful_register_returns_init_without_inquiries(self, agent_ws):
        communicator, init = await connect_and_register(agent_ws, "protocol-agent")

        assert init["type"] == messages.ToAgentMessageType.INIT.value
        assert init["instance_id"] == "protocol-agent"
        assert init["inquiries"] == []

    async def test_blocked_agent_is_rejected(self, agent_ws):
        await _seed_agent("blocked-agent", blocked=True)

        communicator = await agent_ws()
        await send_message(communicator, messages.Register(instance_id="blocked-agent", token=TEST_TOKEN))
        output = await communicator.receive_output(timeout=RECEIVE_TIMEOUT)
        assert output["type"] == "websocket.close"
        assert output["code"] == AGENT_IS_BLOCKED_CODE

    async def test_disconnect_marks_agent_disconnected(self, agent_ws):
        communicator, init = await connect_and_register(agent_ws, "disconnect-agent")
        agent_pk = init["agent"]

        await communicator.disconnect()

        agent = await Agent.objects.aget(pk=agent_pk)
        assert agent.connected is False

    async def test_register_for_uncreated_agent_is_rejected(self, agent_ws):
        # Pins current behavior: on_register can only *find* an agent — its
        # aget_or_create create-branch omits required NOT NULL columns
        # (app/release/device), so registering without a pre-created agent raises
        # and the consumer closes with the schema-mismatch code. If the consumer's
        # create-branch is ever fixed, this test should flip to assert a successful
        # Init instead.
        communicator = await agent_ws()
        await send_message(communicator, messages.Register(instance_id="never-seeded-agent", token=TEST_TOKEN))
        output = await communicator.receive_output(timeout=RECEIVE_TIMEOUT)
        assert output["type"] == "websocket.close"
        assert output["code"] == FROM_AGENT_MESSAGE_DOES_NOT_MATCH_SCHEMA_CODE

    async def test_valid_but_unhandled_message_closes_socket(self, agent_ws):
        # A well-formed FromAgentMessage with no handler hits the ``case _:`` branch
        # in ``receive`` and closes 3003. (Lock/Unlock/Paused/Resumed/Stepped/
        # Interrupted events are currently unhandled by the consumer.)
        communicator, _ = await connect_and_register(agent_ws, "unhandled-agent")
        await send_message(communicator, messages.LockEvent(key="lock-1", assignation=str(uuid.uuid4())))
        output = await communicator.receive_output(timeout=RECEIVE_TIMEOUT)
        assert output["type"] == "websocket.close"
        assert output["code"] == FROM_AGENT_MESSAGE_DOES_NOT_MATCH_SCHEMA_CODE


# --------------------------------------------------------------------------- #
# Tier 2: event persistence
# --------------------------------------------------------------------------- #
@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
class TestAgentEvents:
    async def test_log_event_persists(self, agent_ws):
        assignation = await build_assignation("log")
        communicator, _ = await connect_and_register(agent_ws, "log-agent")

        await send_message(communicator, messages.LogEvent(assignation=str(assignation.pk), message="hello", level="INFO"))

        await communicator.disconnect()  # flush the event through before asserting
        events = [e async for e in AssignationEvent.objects.filter(assignation_id=assignation.pk, kind=enums.AssignationEventKind.LOG)]
        assert len(events) == 1
        assert events[0].message == "hello"

    async def test_progress_event_persists(self, agent_ws):
        assignation = await build_assignation("progress")
        communicator, _ = await connect_and_register(agent_ws, "progress-agent")

        await send_message(communicator, messages.ProgressEvent(assignation=str(assignation.pk), progress=42, message="halfway"))

        await communicator.disconnect()
        event = await AssignationEvent.objects.filter(assignation_id=assignation.pk, kind=enums.AssignationEventKind.PROGRESS).aget()
        assert event.progress == 42
        assert event.message == "halfway"

    async def test_yield_event_persists(self, agent_ws):
        assignation = await build_assignation("yield")
        communicator, _ = await connect_and_register(agent_ws, "yield-agent")

        await send_message(communicator, messages.YieldEvent(assignation=str(assignation.pk), returns={"out": 1}))

        await communicator.disconnect()
        event = await AssignationEvent.objects.filter(assignation_id=assignation.pk, kind=enums.AssignationEventKind.YIELD).aget()
        assert event.returns == {"out": 1}

    async def test_done_event_marks_assignation_done(self, agent_ws):
        assignation = await build_assignation("done")
        communicator, _ = await connect_and_register(agent_ws, "done-agent")

        await send_message(communicator, messages.DoneEvent(assignation=str(assignation.pk)))

        await communicator.disconnect()
        assert await AssignationEvent.objects.filter(assignation_id=assignation.pk, kind=enums.AssignationEventKind.DONE).aexists()
        refreshed = await Assignation.objects.aget(pk=assignation.pk)
        assert refreshed.is_done is True
        assert refreshed.latest_event_kind == enums.AssignationEventKind.DONE
        assert refreshed.finished_at is not None

    async def test_error_event_marks_assignation_done(self, agent_ws):
        assignation = await build_assignation("error")
        communicator, _ = await connect_and_register(agent_ws, "error-agent")

        await send_message(communicator, messages.ErrorEvent(assignation=str(assignation.pk), error="boom"))

        await communicator.disconnect()
        event = await AssignationEvent.objects.filter(assignation_id=assignation.pk, kind=enums.AssignationEventKind.ERROR).aget()
        assert event.message == "boom"
        refreshed = await Assignation.objects.aget(pk=assignation.pk)
        assert refreshed.is_done is True
        assert refreshed.latest_event_kind == enums.AssignationEventKind.ERROR

    async def test_critical_event_marks_assignation_done(self, agent_ws):
        assignation = await build_assignation("critical")
        communicator, _ = await connect_and_register(agent_ws, "critical-agent")

        await send_message(communicator, messages.CriticalEvent(assignation=str(assignation.pk), error="fatal"))

        await communicator.disconnect()
        event = await AssignationEvent.objects.filter(assignation_id=assignation.pk, kind=enums.AssignationEventKind.CRITICAL).aget()
        assert event.message == "fatal"
        refreshed = await Assignation.objects.aget(pk=assignation.pk)
        assert refreshed.latest_event_kind == enums.AssignationEventKind.CRITICAL

    async def test_cancelled_event_marks_assignation_done(self, agent_ws):
        assignation = await build_assignation("cancelled")
        communicator, _ = await connect_and_register(agent_ws, "cancelled-agent")

        await send_message(communicator, messages.CancelledEvent(assignation=str(assignation.pk)))

        await communicator.disconnect()
        assert await AssignationEvent.objects.filter(assignation_id=assignation.pk, kind=enums.AssignationEventKind.CANCELLED).aexists()
        refreshed = await Assignation.objects.aget(pk=assignation.pk)
        assert refreshed.is_done is True
        assert refreshed.latest_event_kind == enums.AssignationEventKind.CANCELLED

    async def test_state_patch_persists(self, agent_ws):
        communicator, init = await connect_and_register(agent_ws, "patch-agent")
        await build_state_for_agent(init["agent"], interface="counter", prefix="patch")

        await send_message(
            communicator,
            messages.StatePatchEvent(
                session_id="session-1", global_rev=1, state_name="counter", ts=0.0,
                op="replace", path="/value", value=5, old_value=None, correlation_id=None,
            ),
        )

        await communicator.disconnect()
        patch = await Patch.objects.filter(agent_id=init["agent"], interface="counter").aget()
        assert patch.op == "replace"
        assert patch.path == "/value"
        assert patch.value == 5
        assert patch.global_rev == 1

    async def test_state_snapshot_persists(self, agent_ws):
        communicator, init = await connect_and_register(agent_ws, "snapshot-agent")
        await build_state_for_agent(init["agent"], interface="counter", prefix="snapshot")

        await send_message(
            communicator,
            messages.StateSnapshotEvent(session_id="session-2", global_rev=3, snapshots={"counter": {"value": 9}}),
        )

        await communicator.disconnect()
        snapshot = await Snapshot.objects.filter(agent_id=init["agent"], global_rev=3).aget()
        assert snapshot.value == {"value": 9}

    async def test_session_init_creates_snapshots(self, agent_ws):
        communicator, init = await connect_and_register(agent_ws, "session-agent")
        await build_state_for_agent(init["agent"], interface="counter", prefix="session")

        await send_message(
            communicator,
            messages.SessionInitMessage(session_id="session-3", states={"counter": {"value": 0}}),
        )

        await communicator.disconnect()
        snapshot = await Snapshot.objects.filter(agent_id=init["agent"]).aget()
        assert snapshot.value == {"value": 0}


# --------------------------------------------------------------------------- #
# Tier 3: redis round-trip + heartbeat timing
# --------------------------------------------------------------------------- #
@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
class TestAgentDelivery:
    async def test_broadcast_is_delivered_to_agent(self, agent_ws):
        communicator, init = await connect_and_register(agent_ws, "delivery-agent")
        agent_pk = init["agent"]

        assign = messages.Assign(
            interface="iface", extension="default", assignation=str(uuid.uuid4()),
            args={"a": 1}, user="1", app="test-app", action="some-action",
        )
        # broadcast() lpushes to the agent's redis queue; listen_for_tasks relays it.
        await sync_to_async(AgentConsumer.broadcast)(agent_pk, assign)

        received = await communicator.receive_json_from(timeout=RECEIVE_TIMEOUT)
        assert received["type"] == messages.ToAgentMessageType.ASSIGN.value
        assert received["assignation"] == assign.assignation
        assert received["args"] == {"a": 1}


# --------------------------------------------------------------------------- #
# Tier 4: AgentProtocol unit tests
#
# These drive the transport-agnostic ``AgentProtocol`` directly with in-memory
# fakes (no Channels, no DB, no redis, no docker, no monkeypatch). They cover the
# protocol/lifecycle/routing/heartbeat decisions that used to require the full
# stack. Run them with ``pytest -k TestAgentProtocolUnit`` with the stack down to
# confirm they have no external dependency.
# --------------------------------------------------------------------------- #
class FakeAgent:
    """Stand-in for the ``Agent`` model the authenticator would return."""

    def __init__(self, pk="agent-1", instance_id="unit-agent", blocked=False):
        self.pk = pk
        self.instance_id = instance_id
        self.blocked = blocked
        self.connected = False
        self.last_seen = None
        self.saves = 0

    async def asave(self):
        self.saves += 1


class FakeBackend:
    """Records which persist-backend hook the protocol routed each message to."""

    def __init__(self, assignations=None):
        self.assignations = assignations or []
        self.calls = []

    async def on_agent_connected(self, agent_id):
        self.calls.append(("connected", agent_id))
        return self.assignations

    async def on_agent_disconnected(self, agent_id):
        self.calls.append(("disconnected", agent_id))

    async def on_agent_log(self, agent_id, message):
        self.calls.append(("log", agent_id, message))


def make_protocol(agent=None, backend=None, queue=None, heartbeat_interval=10.0, heartbeat_timeout=5.0):
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

    protocol = AgentProtocol(
        send=send,
        close=close,
        queue=queue if queue is not None else InMemoryAgentQueue(),
        backend=backend if backend is not None else FakeBackend(),
        authenticator=authenticator,
        heartbeat_interval=heartbeat_interval,
        heartbeat_timeout=heartbeat_timeout,
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


def _register_frame(instance_id="unit-agent", token=TEST_TOKEN):
    return messages.Register(instance_id=instance_id, token=token).model_dump_json()


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

        async def blocking_asave():
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
