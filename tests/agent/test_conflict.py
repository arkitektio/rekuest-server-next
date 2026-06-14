"""Connection-conflict handling — one live connection per agent.

Two communicators share the same token -> same registry -> the SAME single Agent
(agents are unique per registry now). The cross-connection kick runs over the
Channels group layer (``settings_test`` uses the in-process InMemory layer, so a
group_send from one communicator reaches the other in the same process).
"""

import asyncio

import pytest

from facade import enums, messages
from facade.codes import AGENT_ALREADY_CONNECTED_CODE, AGENT_REPLACED_CODE
from facade.models import Agent, AssignationEvent

from tests.agent.helpers import RECEIVE_TIMEOUT, register, send_message
from tests.factories import TEST_TOKEN, build_unimplemented_assignation_for_agent, seed_agent


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
class TestAgentConnectionConflict:
    async def test_second_connection_without_force_is_rejected(self, agent_ws):
        await seed_agent("dup-agent")

        c1 = await agent_ws()
        init1 = await register(c1)
        assert init1["type"] == messages.ToAgentMessageType.INIT.value

        c2 = await agent_ws()
        await send_message(c2, messages.Register(token=TEST_TOKEN, force=False))

        error = await c2.receive_json_from(timeout=RECEIVE_TIMEOUT)
        assert error["type"] == messages.ToAgentMessageType.PROTOCOL_ERROR.value

        output = await c2.receive_output(timeout=RECEIVE_TIMEOUT)
        assert output["type"] == "websocket.close"
        assert output["code"] == AGENT_ALREADY_CONNECTED_CODE

        # The incumbent keeps the agent.
        agent = await Agent.objects.aget(pk=init1["agent"])
        assert agent.connected is True

    async def test_force_connection_kicks_incumbent(self, agent_ws):
        await seed_agent("dup-agent")

        c1 = await agent_ws()
        init1 = await register(c1)

        c2 = await agent_ws()
        init2 = await register(c2, force=True)
        assert init2["type"] == messages.ToAgentMessageType.INIT.value
        assert init2["agent"] == init1["agent"]

        # The incumbent connection is force-closed with the replaced code.
        output = await c1.receive_output(timeout=RECEIVE_TIMEOUT)
        assert output["type"] == "websocket.close"
        assert output["code"] == AGENT_REPLACED_CODE

        # The takeover stays connected: the displaced connection's shutdown must NOT
        # have flipped ``connected`` off (generation guard on active_connection_id).
        agent = await Agent.objects.aget(pk=init1["agent"])
        assert agent.connected is True

    async def test_displaced_connection_does_not_mark_assignations_disconnected(self, agent_ws):
        # Generation guard, end to end: an in-flight assignation owned by the agent
        # must NOT receive a DISCONNECTED event when the incumbent is displaced by a
        # force-register — only a genuine disconnect of the active connection should.
        agent = await seed_agent("dup-agent")
        assignation = await build_unimplemented_assignation_for_agent(agent.pk, "displace-guard")

        c1 = await agent_ws()
        await register(c1)

        c2 = await agent_ws()
        await register(c2, force=True)

        # Let the displaced c1 finish closing/shutting down.
        await c1.receive_output(timeout=RECEIVE_TIMEOUT)
        await asyncio.sleep(0.1)

        disconnected = [
            e
            async for e in AssignationEvent.objects.filter(
                assignation_id=assignation.pk, kind=enums.AssignationEventKind.DISCONNECTED
            )
        ]
        assert disconnected == []
