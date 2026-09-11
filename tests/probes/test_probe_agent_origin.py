"""Agent-originated probes: ProbeRequest over the socket, ...Event mirrors back.

Uses two agents with distinct token identities (the pattern of test_cross_agent): the
REQUESTER fires a ProbeRequest at an implementation owned by the EXECUTOR; the
executor's reports mirror back to the requester's socket as ``…Event`` frames whose
``task`` is the probe id.
"""

import pytest

from facade import messages
from facade.models import Task

from tests.agent.helpers import open_agent
from tests.factories import build_implementation_for_agent


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
class TestAgentOriginProbes:
    async def test_probe_request_round_trip_with_mirrors(self, agent_ws):
        requester = await open_agent(agent_ws, "probe-requester", token="test")
        executor = await open_agent(agent_ws, "probe-executor", token="test2")
        impl = await build_implementation_for_agent(executor.agent.pk, "agent-origin")

        await requester.send(messages.ProbeRequest(reference="ap-1", implementation=str(impl.pk), args={"x": 1}))
        response = await requester.receive(messages.ProbeResponse)
        assert response.error is None
        probe_id = response.probe
        assert probe_id.startswith("p-")
        assert await Task.objects.acount() == 0  # still zero rows

        assign = await executor.receive(messages.Assign)
        assert assign.task == probe_id
        assert assign.probe is True

        await executor.send(messages.Started(task=probe_id))
        await executor.receive(messages.EventAck)
        started = await requester.receive(messages.StartedEvent)
        assert started.task == probe_id

        await executor.send(messages.Yield(task=probe_id, returns={"out": 3}))
        yielded = await requester.receive(messages.YieldEvent)
        assert yielded.task == probe_id
        assert yielded.returns == {"out": 3}

        await executor.send(messages.Completed(task=probe_id))
        await executor.receive(messages.EventAck)
        completed = await requester.receive(messages.CompletedEvent)
        assert completed.task == probe_id
        assert completed.seq > yielded.seq  # per-probe monotonic ordering

    async def test_undeclared_action_nacks(self, agent_ws):
        requester = await open_agent(agent_ws, "probe-requester", token="test")
        executor = await open_agent(agent_ws, "probe-executor", token="test2")
        impl = await build_implementation_for_agent(executor.agent.pk, "agent-origin-decl", allow_probe=False)

        await requester.send(messages.ProbeRequest(implementation=str(impl.pk), args={}))
        response = await requester.receive(messages.ProbeResponse)
        assert response.probe is None
        assert "allow_probe" in response.error

    async def test_executor_disconnect_mirrors_critical(self, agent_ws):
        requester = await open_agent(agent_ws, "probe-requester", token="test")
        executor = await open_agent(agent_ws, "probe-executor", token="test2")
        impl = await build_implementation_for_agent(executor.agent.pk, "agent-origin-dc")

        await requester.send(messages.ProbeRequest(implementation=str(impl.pk), args={}))
        response = await requester.receive(messages.ProbeResponse)
        probe_id = response.probe
        await executor.receive(messages.Assign)

        await executor.disconnect()

        critical = await requester.receive(messages.CriticalEvent)
        assert critical.task == probe_id
        assert "disconnected" in critical.error.lower()
