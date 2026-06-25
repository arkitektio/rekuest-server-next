"""Full-stack agent distributed locks: acquire (Lock) and release (Unlock) over the socket."""

import pytest

from facade import messages
from facade.models import Lock

from tests.agent.helpers import open_agent
from tests.factories import build_task_for_agent_caller


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
class TestAgentLocks:
    async def test_lock_acquires(self, agent_ws):
        session = await open_agent(agent_ws, "lock-acquire-agent")
        task = await build_task_for_agent_caller(session.agent_pk, "lock-acq")
        await Lock.objects.acreate(agent_id=session.agent_pk, key="res-1", description="a resource")

        await session.send(messages.Lock(key="res-1", task=str(task.pk)))
        # disconnect drains the inbound queue, so the Lock is processed before we query.
        await session.disconnect()

        lock = await Lock.objects.aget(agent_id=session.agent_pk, key="res-1")
        assert lock.hold_by_id == task.pk

    async def test_unlock_releases(self, agent_ws):
        session = await open_agent(agent_ws, "lock-release-agent")
        task = await build_task_for_agent_caller(session.agent_pk, "lock-rel")
        await Lock.objects.acreate(agent_id=session.agent_pk, key="res-1", description="a resource", hold_by_id=task.pk)

        await session.send(messages.Unlock(key="res-1"))
        await session.disconnect()

        lock = await Lock.objects.aget(agent_id=session.agent_pk, key="res-1")
        assert lock.hold_by_id is None

    async def test_lock_for_unknown_task_is_ignored(self, agent_ws):
        # A Lock naming a non-existent task must not tear down the socket (and leaves it free).
        session = await open_agent(agent_ws, "lock-unknown-agent")
        await Lock.objects.acreate(agent_id=session.agent_pk, key="res-1", description="a resource")

        await session.send(messages.Lock(key="res-1", task="999999"))
        await session.disconnect()

        lock = await Lock.objects.aget(agent_id=session.agent_pk, key="res-1")
        assert lock.hold_by_id is None
