"""GraphQL-path assign idempotency on (caller, reference).

The agent-socket assign path always deduped resends by reference; the GraphQL path now
does the same: a caller-supplied reference that already names one of this caller's tasks
returns that task — no new row, no re-broadcast.
"""

import pytest
from asgiref.sync import sync_to_async

from facade import inputs
from facade.backend import controll_backend
from facade.models import Task

from tests.agent.helpers import open_agent
from tests.factories import build_implementation_for_agent


class _Info:
    def __init__(self, context):
        self.context = context


async def _assign(authenticated_context, impl_pk, **kwargs):
    model = inputs.AssignInputModel(implementation=str(impl_pk), args={}, **kwargs)
    return await sync_to_async(controll_backend.assign)(_Info(authenticated_context), model)


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
class TestAssignIdempotency:
    async def test_same_reference_returns_prior_task_without_rebroadcast(self, agent_ws, authenticated_context):
        session = await open_agent(agent_ws, "idem-agent")
        impl = await build_implementation_for_agent(session.agent.pk, "idem")

        first = await _assign(authenticated_context, impl.pk, reference="r-idem-1")
        second = await _assign(authenticated_context, impl.pk, reference="r-idem-1")

        assert second.pk == first.pk
        assert await Task.objects.filter(reference="r-idem-1").acount() == 1

        # exactly ONE Assign frame reached the executor
        frame = await session.communicator.receive_json_from(timeout=5)
        assert frame["type"] == "ASSIGN"
        assert frame["task"] == str(first.pk)
        assert await session.communicator.receive_nothing(timeout=0.5)

    async def test_no_reference_always_creates(self, agent_ws, authenticated_context):
        session = await open_agent(agent_ws, "idem-agent")
        impl = await build_implementation_for_agent(session.agent.pk, "idem-none")

        first = await _assign(authenticated_context, impl.pk)
        second = await _assign(authenticated_context, impl.pk)
        assert first.pk != second.pk

    async def test_init_hook_children_stay_distinct_per_parent(self, agent_ws, authenticated_context):
        from facade.caller_context import CallerContext

        session = await open_agent(agent_ws, "idem-agent")
        impl = await build_implementation_for_agent(session.agent.pk, "idem-hook")

        # The hook's action_hash lookup is org-scoped, so assign under the agent's own
        # identity (same org as the seeded action).
        ctx = CallerContext.from_agent(session.agent)
        hook = inputs.HookInputModel(kind="INIT", hash="idem-hook-action-hash")
        model = inputs.AssignInputModel(implementation=str(impl.pk), args={}, hooks=[hook])
        first = await sync_to_async(controll_backend.assign)(ctx, model)
        second = await sync_to_async(controll_backend.assign)(ctx, model)
        assert first.pk != second.pk

        # each parent got its OWN hook child (the old constant reference would have
        # deduped the second parent's hook onto the first parent's child)
        first_children = [t async for t in Task.objects.filter(parent=first)]
        second_children = [t async for t in Task.objects.filter(parent=second)]
        assert len(first_children) == 1
        assert len(second_children) == 1
        assert first_children[0].pk != second_children[0].pk
