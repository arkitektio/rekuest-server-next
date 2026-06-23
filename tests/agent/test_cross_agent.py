"""Cross-agent dispatch: one agent (the caller) assigns work to a *different* agent (the executor).

Two distinct identities (two static tokens → two Agents in the same org) connect over two
sockets. The caller originates a ``AssignRequest`` targeting the executor's implementation; the
backend dispatches the ``Assign`` to the executor, and — because the caller is the
assignation's caller — the executor's events flow back to the caller as ``Caller*`` mirrors.

The executor connects first so it is available for resolution and receives the broadcast.
"""

import pytest

from facade import messages
from facade.models import Assignation

from tests.agent.helpers import open_agent
from tests.factories import build_implementation_for_agent

EXECUTOR_TOKEN = "test2"  # a second identity, distinct from the default "test"


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
class TestCrossAgentAssign:
    async def test_caller_assigns_to_a_different_executor(self, agent_ws):
        executor = await open_agent(agent_ws, "executor-agent", token=EXECUTOR_TOKEN)
        impl = await build_implementation_for_agent(executor.agent_pk, "xagent")
        caller = await open_agent(agent_ws, "caller-agent")  # default token → a different identity

        # The caller originates work targeting the *executor's* implementation.
        await caller.send(messages.AssignRequest(reference="x-1", implementation=str(impl.pk), args={"k": 1}))
        result = await caller.receive(messages.AssignResponse)
        assert result.created is True and result.assignation

        # The executor (a DIFFERENT agent) receives the dispatched ASSIGN command.
        assign = await executor.receive(messages.Assign)
        assert assign.assignation == result.assignation
        assert assign.interface == impl.interface and assign.args == {"k": 1}

        # The assignation is owned by the executor but called by the caller.
        ass = await Assignation.objects.select_related("caller").aget(id=result.assignation)
        assert ass.agent_id == executor.agent_pk
        assert ass.agent_id != caller.agent_pk
        assert ass.caller.client_id == caller.agent.client_id

        await caller.disconnect()
        await executor.disconnect()

    async def test_executor_events_flow_back_to_the_caller(self, agent_ws):
        executor = await open_agent(agent_ws, "executor2-agent", token=EXECUTOR_TOKEN)
        impl = await build_implementation_for_agent(executor.agent_pk, "xagent2")
        caller = await open_agent(agent_ws, "caller2-agent")

        await caller.send(messages.AssignRequest(reference="x-2", implementation=str(impl.pk), args={}))
        result = await caller.receive(messages.AssignResponse)
        assign = await executor.receive(messages.Assign)

        # The executor reports progress, then done — over its OWN socket.
        await executor.send(messages.Progress(assignation=assign.assignation, progress=50, message="half"))
        progress = await caller.receive(messages.ProgressEvent)
        assert progress.assignation == result.assignation and progress.progress == 50

        await executor.send(messages.Completed(assignation=assign.assignation))
        done = await caller.receive(messages.CompletedEvent)
        assert done.assignation == result.assignation

        await caller.disconnect()
        await executor.disconnect()

    async def test_assign_by_action_routes_to_the_providing_executor(self, agent_ws):
        # No implementation id — the caller assigns by action, and the backend auto-routes to
        # the only connected agent that provides it (the executor).
        executor = await open_agent(agent_ws, "executor3-agent", token=EXECUTOR_TOKEN)
        impl = await build_implementation_for_agent(executor.agent_pk, "xagent3")
        caller = await open_agent(agent_ws, "caller3-agent")

        await caller.send(messages.AssignRequest(reference="x-3", action=str(impl.action_id), args={"v": 7}))
        result = await caller.receive(messages.AssignResponse)
        assert result.created is True

        assign = await executor.receive(messages.Assign)
        assert assign.assignation == result.assignation and assign.args == {"v": 7}

        await caller.disconnect()
        await executor.disconnect()
