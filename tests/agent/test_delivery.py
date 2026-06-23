"""Redis round-trip: a backend ``broadcast`` is relayed to the connected agent."""

import uuid

import pytest
from asgiref.sync import sync_to_async

from facade import messages
from facade.consumers.async_consumer import AgentConsumer

from tests.agent.helpers import open_agent


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
class TestAgentDelivery:
    async def test_broadcast_is_delivered_to_agent(self, agent_ws):
        session = await open_agent(agent_ws, "delivery-agent")

        assign = messages.Assign(
            interface="iface", task=str(uuid.uuid4()),
            args={"a": 1}, user="1", org="test-org", action="some-action",
            implementation="impl-1",
        )
        # broadcast() lpushes to the agent's redis queue; listen_for_tasks relays it.
        await sync_to_async(AgentConsumer.broadcast)(session.agent_pk, assign)

        received = await session.receive(messages.Assign)
        assert received.task == assign.task
        assert received.args == {"a": 1}
