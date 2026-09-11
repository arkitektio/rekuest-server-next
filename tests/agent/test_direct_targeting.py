"""agent+interface targeting and the dependency min-viable-instances guard."""

import pytest
from asgiref.sync import sync_to_async

from facade import inputs, messages
from facade.backend import build_dependency_dict, controll_backend
from facade.caller_context import CallerContext
from facade.models import Dependency

from tests.agent.helpers import open_agent
from tests.factories import build_implementation_for_agent


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
class TestAgentInterfaceTargeting:
    async def test_graphql_path_assigns_by_agent_and_interface(self, agent_ws):
        session = await open_agent(agent_ws, "target-agent", token="test")
        impl = await build_implementation_for_agent(session.agent.pk, "target-direct")

        ctx = CallerContext.from_agent(session.agent)
        task = await sync_to_async(controll_backend.assign)(
            ctx,
            inputs.AssignInputModel(agent=str(session.agent.pk), interface=impl.interface, args={}, step=True),
        )
        assert task.implementation_id == impl.pk

        assign = await session.receive(messages.Assign)
        assert assign.task == str(task.pk)
        assert assign.interface == impl.interface
        assert assign.step is True  # the wired-through step flag

    async def test_socket_assign_request_by_agent_and_interface(self, agent_ws):
        requester = await open_agent(agent_ws, "target-requester", token="test")
        executor = await open_agent(agent_ws, "target-executor", token="test2")
        impl = await build_implementation_for_agent(executor.agent.pk, "target-socket")

        from tests.factories import build_task

        parent = await build_task("target-parent")
        await requester.send(messages.AssignRequest(reference="tgt-1", agent=str(executor.agent.pk), interface=impl.interface, parent=str(parent.pk), args={}))
        response = await requester.receive(messages.AssignResponse)
        assert response.error is None, response.error
        assert response.task is not None

        assign = await executor.receive(messages.Assign)
        assert assign.task == response.task
        assert assign.interface == impl.interface


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
class TestMinViableInstances:
    async def test_min_viable_counted_before_truncation(self, agent_ws):
        session = await open_agent(agent_ws, "minv-agent", token="test")
        impl = await build_implementation_for_agent(session.agent.pk, "minv")

        def _check():
            # One available agent, min 2: must raise — the historic code checked min
            # against the already-truncated slice, so with max=1 it could never trip.
            Dependency.objects.create(
                implementation=impl,
                key="dep",
                app_filter=session.agent.app.identifier,
                min_viable_instances=2,
                max_viable_instances=1,
                auto_resolvable=True,
            )
            ctx = CallerContext.from_agent(session.agent)
            with pytest.raises(ValueError, match="Required at least 2"):
                build_dependency_dict(impl, ctx, [])

        await sync_to_async(_check)()
