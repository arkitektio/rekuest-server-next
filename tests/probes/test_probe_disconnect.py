"""Agent death fails live probes immediately — no grace window, no reconcile sweep."""

import pytest
from asgiref.sync import sync_to_async

from facade import inputs, messages
from facade.probes.backend import probe_backend
from facade.probes.store import get_probe_store

from tests.agent.helpers import open_agent
from tests.factories import build_implementation_for_agent


class _Info:
    def __init__(self, context):
        self.context = context


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
class TestCallDisconnect:
    async def test_disconnect_criticals_live_calls(self, agent_ws, authenticated_context):
        session = await open_agent(agent_ws, "dc-agent")
        impl = await build_implementation_for_agent(session.agent.pk, "probe-dc")

        state = await sync_to_async(probe_backend.probe)(_Info(authenticated_context), inputs.ProbeInputModel(implementation=str(impl.pk), args={}))
        probe_id = state["id"]
        await session.receive(messages.Assign)

        await session.disconnect()

        state = await get_probe_store().aget(probe_id)
        assert state["done"] == "CRITICAL"
        assert state["err"] == "Agent disconnected"

    async def test_finished_calls_are_untouched_by_disconnect(self, agent_ws, authenticated_context):
        session = await open_agent(agent_ws, "dc-agent")
        impl = await build_implementation_for_agent(session.agent.pk, "probe-dc2")

        state = await sync_to_async(probe_backend.probe)(_Info(authenticated_context), inputs.ProbeInputModel(implementation=str(impl.pk), args={}))
        probe_id = state["id"]
        await session.receive(messages.Assign)
        await session.send(messages.Completed(task=probe_id))
        await session.receive(messages.EventAck)

        await session.disconnect()

        state = await get_probe_store().aget(probe_id)
        assert state["done"] == "COMPLETED"
