"""Full-stack agent protocol/lifecycle tests.

These drive the real ``AgentConsumer`` (``facade/consumers/async_consumer.py``)
through Django Channels' ``WebsocketCommunicator`` against real Postgres and real
Redis (both started by the ``backend_stack`` dokker fixture in ``conftest.py``).

``default_authenticator`` only *finds* an existing agent — its ``aget_or_create``
create-branch omits the required ``app``/``release`` columns, so
brand-new agents cannot be created over the socket. In normal operation the agent
is created first via the ``ensureAgent`` GraphQL mutation and then connects;
``seed_agent`` reproduces that by pre-creating the agent against the exact identity
the consumer derives from the token, so registration takes the get-branch.
"""

import uuid

import pytest

from facade import enums, messages
from facade.codes import (
    AGENT_IS_BLOCKED_CODE,
    FROM_AGENT_MESSAGE_DOES_NOT_MATCH_SCHEMA_CODE,
    FROM_AGENT_MESSAGE_IS_NOT_VALID_JSON_CODE,
)
from facade.models import Agent, AssignationEvent

from tests.agent.helpers import RECEIVE_TIMEOUT, connect_and_register, register, send_message
from tests.factories import TEST_TOKEN, build_unimplemented_assignation_for_agent, seed_agent


# --------------------------------------------------------------------------- #
# Tier 1: walking skeleton (must be green inside the full suite before the rest)
# --------------------------------------------------------------------------- #
@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
class TestAgentWalkingSkeleton:
    async def test_register_returns_init_for_seeded_agent(self, agent_ws):
        agent = await seed_agent("skeleton-agent")

        communicator = await agent_ws()
        init = await register(communicator, instance_id="skeleton-agent")

        assert init["type"] == messages.ToAgentMessageType.INIT.value
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
        assert init["inquiries"] == []

    async def test_blocked_agent_is_rejected(self, agent_ws):
        await seed_agent("blocked-agent", blocked=True)

        communicator = await agent_ws()
        await send_message(communicator, messages.Register(token=TEST_TOKEN))
        output = await communicator.receive_output(timeout=RECEIVE_TIMEOUT)
        assert output["type"] == "websocket.close"
        assert output["code"] == AGENT_IS_BLOCKED_CODE

    async def test_disconnect_marks_agent_disconnected(self, agent_ws):
        communicator, init = await connect_and_register(agent_ws, "disconnect-agent")
        agent_pk = init["agent"]

        await communicator.disconnect()

        agent = await Agent.objects.aget(pk=agent_pk)
        assert agent.connected is False

    async def test_disconnect_marks_unimplemented_assignation(self, agent_ws):
        # Regression (B1): an unfinished assignation owned directly by the agent
        # but with a null implementation must still get a DISCONNECTED event on
        # disconnect. The handler previously filtered by ``implementation__agent``
        # and silently skipped these rows.
        agent = await seed_agent("disconnect-unimpl-agent")
        assignation = await build_unimplemented_assignation_for_agent(agent.pk, "disc-unimpl")

        communicator = await agent_ws()
        await register(communicator, instance_id="disconnect-unimpl-agent")
        await communicator.disconnect()

        events = [
            e
            async for e in AssignationEvent.objects.filter(
                assignation_id=assignation.pk, kind=enums.AssignationEventKind.DISCONNECTED
            )
        ]
        assert len(events) == 1

    async def test_register_for_uncreated_agent_is_rejected(self, agent_ws):
        # Pins current behavior: on_register can only *find* an agent — its
        # aget_or_create create-branch omits required NOT NULL columns
        # (app/release), so registering without a pre-created agent raises
        # and the consumer closes with the schema-mismatch code. If the consumer's
        # create-branch is ever fixed, this test should flip to assert a successful
        # Init instead.
        communicator = await agent_ws()
        await send_message(communicator, messages.Register(token=TEST_TOKEN))
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
