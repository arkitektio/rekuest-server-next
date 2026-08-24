"""Pause/resume for probes: two-phase like cancel, idempotent on terminal probes."""

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
class TestProbePauseResume:
    async def test_pause_resume_round_trip(self, agent_ws, authenticated_context):
        session = await open_agent(agent_ws, "pause-agent")
        impl = await build_implementation_for_agent(session.agent.pk, "probe-pause")

        info = _Info(authenticated_context)
        state = await sync_to_async(probe_backend.probe)(info, inputs.ProbeInputModel(implementation=str(impl.pk), args={}))
        probe_id = state["id"]
        await session.receive(messages.Assign)

        state = await sync_to_async(probe_backend.pause)(info, probe_id)
        assert state["kind"] == "PAUSING"
        pause = await session.receive(messages.Pause)
        assert pause.task == probe_id

        await session.send(messages.Paused(task=probe_id))
        await session.receive(messages.EventAck)
        assert (await get_probe_store().aget(probe_id))["kind"] == "PAUSED"

        state = await sync_to_async(probe_backend.resume)(info, probe_id)
        assert state["kind"] == "RESUMING"
        resume = await session.receive(messages.Resume)
        assert resume.task == probe_id

        await session.send(messages.Resumed(task=probe_id))
        await session.receive(messages.EventAck)
        await session.send(messages.Completed(task=probe_id))
        await session.receive(messages.EventAck)
        assert (await get_probe_store().aget(probe_id))["done"] == "COMPLETED"

    async def test_pause_on_terminal_probe_is_idempotent(self, agent_ws, authenticated_context):
        session = await open_agent(agent_ws, "pause-agent")
        impl = await build_implementation_for_agent(session.agent.pk, "probe-pause-idem")

        info = _Info(authenticated_context)
        state = await sync_to_async(probe_backend.probe)(info, inputs.ProbeInputModel(implementation=str(impl.pk), args={}))
        probe_id = state["id"]
        await session.receive(messages.Assign)
        await session.send(messages.Completed(task=probe_id))
        await session.receive(messages.EventAck)

        state = await sync_to_async(probe_backend.pause)(info, probe_id)
        assert state["done"] == "COMPLETED"  # no error, terminal state returned

    async def test_pause_requires_ownership(self, agent_ws, authenticated_context):
        from facade.caller_context import CallerContext

        session = await open_agent(agent_ws, "pause-agent")
        impl = await build_implementation_for_agent(session.agent.pk, "probe-pause-own")

        state = await sync_to_async(probe_backend.probe)(_Info(authenticated_context), inputs.ProbeInputModel(implementation=str(impl.pk), args={}))
        await session.receive(messages.Assign)

        # A genuinely different identity (token "test2"), not merely a different fixture. This
        # used to rely on ``authenticated_context`` and ``seed_agent`` disagreeing about the
        # organization, which was a fixture bug rather than a foreign caller.
        other_agent = await seed_agent("probe-foreign", token="test2")
        foreign = await sync_to_async(CallerContext.from_agent)(other_agent)
        with pytest.raises(PermissionError):
            await sync_to_async(probe_backend.pause)(foreign, state["id"])
