"""Redis round-trip: a backend ``broadcast`` is relayed to the connected agent."""

import uuid

import pytest
from asgiref.sync import sync_to_async

from facade import messages
from facade.consumers.async_consumer import AgentConsumer

from tests.agent.helpers import RECEIVE_TIMEOUT, connect_and_register


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
