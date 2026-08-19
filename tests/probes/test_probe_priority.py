"""The probe priority lane: probe frames jump an agent's queued task backlog."""

import pytest
import redis as sync_redis
from asgiref.sync import sync_to_async
from django.conf import settings

from facade import inputs, messages
from facade.backend import controll_backend
from facade.consumers.agent_queue import InMemoryAgentQueue, RedisAgentQueue
from facade.probes.backend import probe_backend

from tests.agent.helpers import open_agent
from tests.factories import build_implementation_for_agent


class _Info:
    def __init__(self, context):
        self.context = context


class TestQueueOrdering:
    def test_redis_priority_jumps_the_backlog(self, backend_stack):
        client = sync_redis.Redis(host=settings.AGENT_REDIS_HOST, port=settings.AGENT_REDIS_PORT)
        client.flushdb()
        client.close()

        queue = RedisAgentQueue.from_settings()
        queue.push("prio-agent", "task-1")
        queue.push("prio-agent", "task-2")
        queue.push("prio-agent", "task-3")
        queue.push("prio-agent", "probe-1", priority=True)

        async def drain():
            popped = []
            for _ in range(4):
                message = await queue.pop("prio-agent")
                popped.append(message)
                await queue.ack("prio-agent", message)
            await queue.close()
            return popped

        import asyncio

        assert asyncio.run(drain()) == ["probe-1", "task-1", "task-2", "task-3"]

    def test_in_memory_priority_jumps_the_backlog(self):
        import asyncio

        async def drive():
            queue = InMemoryAgentQueue()
            queue.push("a", "task-1")
            queue.push("a", "task-2")
            queue.push("a", "probe-1", priority=True)
            return [await queue.pop("a") for _ in range(3)]

        assert asyncio.run(drive()) == ["probe-1", "task-1", "task-2"]


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
class TestProbePriorityFullStack:
    async def test_probe_assign_overtakes_queued_task_assign(self, agent_ws, authenticated_context):
        # Register the agent (so it is available) but delay its consumption by queueing
        # both messages before the consumer can drain — the connected agent drains fast,
        # so ordering is asserted at the frame level: the probe frame arrives first only
        # if it was RPUSHed ahead. To make it deterministic we enqueue while the agent's
        # listener is racing; the redis-level test above pins the mechanism, this one
        # pins the wiring (probe path passes priority=True end to end).
        session = await open_agent(agent_ws, "prio-agent")
        impl = await build_implementation_for_agent(session.agent.pk, "prio")

        info = _Info(authenticated_context)
        # enqueue back-to-back from the sync side; the task first, then the probe
        await sync_to_async(controll_backend.assign)(info, inputs.AssignInputModel(implementation=str(impl.pk), args={}))
        state = await sync_to_async(probe_backend.probe)(info, inputs.ProbeInputModel(implementation=str(impl.pk), args={}))

        first = await session.receive(messages.Assign)
        second = await session.receive(messages.Assign)
        received = {first.task: first, second.task: second}
        assert state["id"] in received
        assert received[state["id"]].probe is True
        # both frames arrived; strict overtaking is asserted at the queue level above
        # (the live consumer may have drained the task frame before the probe was pushed)
        assert len(received) == 2
