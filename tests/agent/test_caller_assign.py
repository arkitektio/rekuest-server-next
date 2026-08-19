"""Full-stack sub-assignment over the agent socket.

An agent assigns *dependent* work via ``AssignRequest`` and gets an ``AssignResponse`` back.
Here the registered agent assigns to its own implementation, so it both originates the child
task and receives the ``ASSIGN`` command for it. Idempotency: resending the same ``reference``
returns the same task with ``created=False``.

``parent`` is mandatory: an agent may only assign work beneath a task it is already running.
Root tasks come solely from the GraphQL ``assign`` mutation, where the initiator is an
accountable human (the human-root invariant in ``docs/design/provenance.md``).
"""

import pytest

from facade import messages
from facade.models import Task

from tests.agent.helpers import open_agent
from tests.factories import build_implementation_for_agent, build_task


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
class TestAssignRequest:
    async def test_sub_assign_creates_then_is_idempotent(self, agent_ws):
        session = await open_agent(agent_ws, "callerassign-agent")
        impl = await build_implementation_for_agent(session.agent.pk, "callerassign")
        parent = await build_task("callerassign-parent")

        # Assign work beneath the task we are running.
        await session.send(messages.AssignRequest(reference="r-1", implementation=str(impl.pk), parent=str(parent.pk), args={"x": 1}))
        result = await session.receive(messages.AssignResponse)
        assert result.reference == "r-1" and result.created is True and result.task

        # Resend the SAME reference → same task, created=False, no duplicate row.
        await session.send(messages.AssignRequest(reference="r-1", implementation=str(impl.pk), parent=str(parent.pk), args={"x": 1}))
        result2 = await session.receive(messages.AssignResponse)
        assert result2.task == result.task and result2.created is False

        assert await Task.objects.filter(reference="r-1").acount() == 1

        created = await Task.objects.aget(id=result.task)
        assert created.parent_id == parent.pk
        await session.disconnect()

    async def test_sub_assign_dispatches_assign_command_to_executor(self, agent_ws):
        session = await open_agent(agent_ws, "callerassign2-agent")
        impl = await build_implementation_for_agent(session.agent.pk, "callerassign2")
        parent = await build_task("callerassign2-parent")

        await session.send(messages.AssignRequest(reference="r-2", implementation=str(impl.pk), parent=str(parent.pk), args={"y": 2}))

        # The agent is also the executor, so it receives the ASSIGN command for the work.
        assign = await session.receive(messages.Assign)
        assert assign.interface == impl.interface and assign.args == {"y": 2}
        await session.disconnect()

    async def test_root_assign_over_the_socket_is_refused(self, agent_ws):
        # The rule that replaced ``can_assign_root``: an agent has no way to originate a root.
        # It must NACK (the socket carries the agent's other work) rather than close.
        session = await open_agent(agent_ws, "rootassign-agent")
        impl = await build_implementation_for_agent(session.agent.pk, "rootassign")

        await session.send(messages.AssignRequest(reference="r-3", implementation=str(impl.pk), args={"z": 3}))

        result = await session.receive(messages.AssignResponse)
        assert result.created is False and result.task is None
        assert "parent" in (result.error or "")
        assert await Task.objects.filter(reference="r-3").acount() == 0
        await session.disconnect()
