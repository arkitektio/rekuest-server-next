"""Root propagation on assign-created descendants + the audit/behavior it unlocks.

``Task.root`` used to be set only on the higher-order lower task, so interrupt's
descendant propagation (``filter(root_id=…)``) found nothing for ordinary children and
children leaked into the root feeds. These tests pin the fixed behavior, plus the
``TaskInstruct`` audit rows control ops now write.
"""

import pytest
from asgiref.sync import sync_to_async

from facade import enums, inputs, messages
from facade.backend import controll_backend
from facade.models import Task, TaskInstruct

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
class TestRootPropagation:
    async def test_assign_chain_sets_root(self, agent_ws, authenticated_context):
        session = await open_agent(agent_ws, "root-agent")
        impl = await build_implementation_for_agent(session.agent.pk, "root-chain")

        root = await _assign(authenticated_context, impl.pk)
        child = await _assign(authenticated_context, impl.pk, parent=str(root.pk))
        grandchild = await _assign(authenticated_context, impl.pk, parent=str(child.pk))

        assert root.root_id is None
        assert child.root_id == root.pk
        assert grandchild.root_id == root.pk  # the ROOT, not the direct parent

        # the wire message carries the lineage too
        first = await session.receive(messages.Assign)
        assert first.root is None
        second = await session.receive(messages.Assign)
        assert second.root == str(root.pk)
        assert second.parent == str(root.pk)
        third = await session.receive(messages.Assign)
        assert third.root == str(root.pk)
        assert third.parent == str(child.pk)

    async def test_interrupt_propagates_to_assign_created_descendants(self, agent_ws, authenticated_context):
        session = await open_agent(agent_ws, "root-agent")
        impl = await build_implementation_for_agent(session.agent.pk, "root-int")

        root = await _assign(authenticated_context, impl.pk)
        child = await _assign(authenticated_context, impl.pk, parent=str(root.pk))
        grandchild = await _assign(authenticated_context, impl.pk, parent=str(child.pk))
        for _ in range(3):
            await session.receive(messages.Assign)

        caller = await sync_to_async(lambda: root.caller)()
        await sync_to_async(controll_backend.interrupt)(inputs.InterruptInputModel(task=str(root.pk)), caller)

        # every member of the tree got the Interrupt frame
        interrupted = {(await session.receive(messages.Interrupt)).task for _ in range(3)}
        assert interrupted == {str(root.pk), str(child.pk), str(grandchild.pk)}

        # and each target carries a TaskInstruct audit row naming the requester
        instructs = [i async for i in TaskInstruct.objects.filter(kind=enums.TaskInstructChoices.INTERRUPT)]
        assert {i.task_id for i in instructs} == {root.pk, child.pk, grandchild.pk}
        assert all(i.caller_id == caller.pk for i in instructs)

    async def test_children_stay_out_of_my_tasks(self, agent_ws, authenticated_context):
        session = await open_agent(agent_ws, "root-agent")
        impl = await build_implementation_for_agent(session.agent.pk, "root-feed")

        root = await _assign(authenticated_context, impl.pk)
        await _assign(authenticated_context, impl.pk, parent=str(root.pk))

        caller_id = await sync_to_async(lambda: root.caller_id)()
        roots = [t async for t in Task.objects.filter(caller_id=caller_id, root__isnull=True)]
        assert [t.pk for t in roots] == [root.pk]
