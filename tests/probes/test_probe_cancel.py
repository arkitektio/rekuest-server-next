"""Cancel is first-class for probes (hover-away): cheap, two-phase, and idempotent."""

import pytest
from asgiref.sync import sync_to_async

from facade import inputs, messages
from facade.probes.backend import probe_backend
from facade.probes.store import get_probe_store

from tests.agent.helpers import open_agent
from tests.factories import build_implementation_for_agent, seed_agent


class _Info:
    def __init__(self, context):
        self.context = context


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
class TestCallCancel:
    async def test_cancel_round_trip(self, agent_ws, authenticated_context):
        session = await open_agent(agent_ws, "cancel-agent")
        impl = await build_implementation_for_agent(session.agent.pk, "probe-cancel")

        info = _Info(authenticated_context)
        state = await sync_to_async(probe_backend.probe)(info, inputs.ProbeInputModel(implementation=str(impl.pk), args={}))
        probe_id = state["id"]
        await session.receive(messages.Assign)

        state = await sync_to_async(probe_backend.cancel)(info, probe_id)
        assert state["kind"] == "CANCELLING"

        cancel = await session.receive(messages.Cancel)
        assert cancel.task == probe_id

        # the agent confirms; the probe closes as CANCELLED
        await session.send(messages.Cancelled(task=probe_id))
        await session.receive(messages.EventAck)
        state = await get_probe_store().aget(probe_id)
        assert state["done"] == "CANCELLED"

        # hover-away races completion constantly: cancelling a finished probe is a no-op
        state = await sync_to_async(probe_backend.cancel)(info, probe_id)
        assert state["done"] == "CANCELLED"

    async def test_cancel_requires_ownership(self, agent_ws, authenticated_context):
        session = await open_agent(agent_ws, "cancel-agent")
        impl = await build_implementation_for_agent(session.agent.pk, "probe-owner")

        info = _Info(authenticated_context)
        state = await sync_to_async(probe_backend.probe)(info, inputs.ProbeInputModel(implementation=str(impl.pk), args={}))
        probe_id = state["id"]
        await session.receive(messages.Assign)

        # a different identity (the agent's own) is not the caller
        from facade.caller_context import CallerContext

        # A genuinely different identity (token "test2"), not merely a different fixture. This
        # used to rely on ``authenticated_context`` and ``seed_agent`` disagreeing about the
        # organization, which was a fixture bug rather than a foreign caller.
        other_agent = await seed_agent("probe-foreign", token="test2")
        foreign = await sync_to_async(CallerContext.from_agent)(other_agent)
        with pytest.raises(PermissionError):
            await sync_to_async(probe_backend.cancel)(foreign, probe_id)
