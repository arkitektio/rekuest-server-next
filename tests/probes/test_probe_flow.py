"""Full-stack probe flow: mutation backend → agent socket → redis state.

The task twin of ``test_provenance_dispatch`` — but asserting ZERO database rows: the
agent receives a perfectly normal Assign whose task id is a ``p-`` probe id, its reports
land in redis, and the Task/TaskEvent tables never grow.
"""

import pytest
from asgiref.sync import sync_to_async
from joserfc import jwt
from joserfc.jwk import KeySet

from facade import inputs, messages
from facade.probes.backend import probe_backend
from facade.probes.ids import is_probe_id
from facade.probes.store import get_probe_store
from facade.models import Task, TaskEvent
from facade.provenance import keys

from tests.agent.helpers import open_agent
from tests.factories import build_implementation_for_agent


class _Info:
    def __init__(self, context):
        self.context = context


def _decode(token):
    return jwt.decode(token, KeySet([keys.get_public_key()]), algorithms=keys.ALGORITHMS)


async def _fire_call(authenticated_context, impl_pk, **kwargs):
    model = inputs.ProbeInputModel(implementation=str(impl_pk), args={"x": 1}, **kwargs)
    return await sync_to_async(probe_backend.probe)(_Info(authenticated_context), model)


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
class TestCallFlow:
    async def test_call_dispatches_assign_and_persists_nothing(self, agent_ws, authenticated_context):
        session = await open_agent(agent_ws, "probe-agent")
        impl = await build_implementation_for_agent(session.agent.pk, "probe-flow")

        tasks_before = await Task.objects.acount()
        state = await _fire_call(authenticated_context, impl.pk)
        probe_id = state["id"]
        assert is_probe_id(probe_id)

        assign = await session.receive(messages.Assign)
        assert assign.task == probe_id
        assert assign.args == {"x": 1}
        assert assign.probe is True  # the agent is told this is a probe, not a task

        # provenance: a probe is always its own root
        claims = _decode(assign.token).claims
        assert claims["tsk"] == probe_id
        assert claims["rtk"] == probe_id
        assert claims["ptk"] is None

        # the whole exchange left the database untouched
        assert await Task.objects.acount() == tasks_before
        assert await TaskEvent.objects.acount() == 0

    async def test_probe_events_land_in_redis_not_the_db(self, agent_ws, authenticated_context):
        session = await open_agent(agent_ws, "probe-agent")
        impl = await build_implementation_for_agent(session.agent.pk, "probe-events")

        state = await _fire_call(authenticated_context, impl.pk)
        probe_id = state["id"]
        await session.receive(messages.Assign)

        store = get_probe_store()

        await session.send(messages.Started(task=probe_id))
        await session.receive(messages.EventAck)
        state = await store.aget(probe_id)
        assert state["kind"] == "STARTED"

        await session.send(messages.Yield(task=probe_id, returns={"out": 41}))
        await session.send(messages.Completed(task=probe_id))
        ack = await session.receive(messages.EventAck)
        assert ack.task == probe_id

        state = await store.aget(probe_id)
        assert state["done"] == "COMPLETED"
        assert state["kind"] == "COMPLETED"
        assert '"out": 41' in state["last_returns"]
        assert int(state["seq"]) == 3  # STARTED, YIELD, COMPLETED

        assert await TaskEvent.objects.acount() == 0

    async def test_task_assigns_are_not_marked_probe(self, agent_ws, authenticated_context):
        from facade.backend import controll_backend

        session = await open_agent(agent_ws, "probe-agent")
        impl = await build_implementation_for_agent(session.agent.pk, "probe-vs-task")

        await sync_to_async(controll_backend.assign)(_Info(authenticated_context), inputs.AssignInputModel(implementation=str(impl.pk), args={}))
        assign = await session.receive(messages.Assign)
        assert not is_probe_id(assign.task)
        assert assign.probe is False

    async def test_resent_terminal_is_deduped(self, agent_ws, authenticated_context):
        session = await open_agent(agent_ws, "probe-agent")
        impl = await build_implementation_for_agent(session.agent.pk, "probe-dedup")

        state = await _fire_call(authenticated_context, impl.pk)
        probe_id = state["id"]
        await session.receive(messages.Assign)

        await session.send(messages.Completed(task=probe_id))
        await session.receive(messages.EventAck)
        await session.send(messages.Completed(task=probe_id))  # a retry — still acked, not re-applied
        await session.receive(messages.EventAck)

        state = await get_probe_store().aget(probe_id)
        assert state["done"] == "COMPLETED"
        assert int(state["seq"]) == 1
