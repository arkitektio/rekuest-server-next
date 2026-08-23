"""What a probe refuses — everything that needs a Task row to be sound."""

import pytest
from asgiref.sync import sync_to_async
from django.test import override_settings

from facade import inputs, messages
from facade.probes.backend import probe_backend
from facade.models import Dependency, Implementation

from tests.agent.helpers import open_agent
from tests.factories import build_implementation_for_agent


class _Info:
    def __init__(self, context):
        self.context = context


def _add_dependency(impl_pk):
    return Dependency.objects.create(implementation_id=impl_pk, key="dep")


def _make_higher_order(higher_pk, lower_pk):
    Implementation.objects.filter(pk=higher_pk).update(higher_order_for_id=lower_pk)


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
class TestCallGuards:
    async def test_undeclared_actions_are_refused(self, agent_ws, authenticated_context):
        session = await open_agent(agent_ws, "guard-agent")
        impl = await build_implementation_for_agent(session.agent.pk, "guard-decl", allow_probe=False)

        with pytest.raises(ValueError, match="allow_probe"):
            await sync_to_async(probe_backend.probe)(_Info(authenticated_context), inputs.ProbeInputModel(implementation=str(impl.pk), args={}))

    async def test_dependency_implementations_are_refused(self, agent_ws, authenticated_context):
        session = await open_agent(agent_ws, "guard-agent")
        impl = await build_implementation_for_agent(session.agent.pk, "guard-dep")
        await sync_to_async(_add_dependency)(impl.pk)

        with pytest.raises(ValueError, match="dependencies"):
            await sync_to_async(probe_backend.probe)(_Info(authenticated_context), inputs.ProbeInputModel(implementation=str(impl.pk), args={}))

    async def test_higher_order_implementations_are_refused(self, agent_ws, authenticated_context):
        session = await open_agent(agent_ws, "guard-agent")
        higher = await build_implementation_for_agent(session.agent.pk, "guard-ho-higher")
        lower = await build_implementation_for_agent(session.agent.pk, "guard-ho-lower")
        await sync_to_async(_make_higher_order)(higher.pk, lower.pk)

        with pytest.raises(ValueError, match="higher-order"):
            await sync_to_async(probe_backend.probe)(_Info(authenticated_context), inputs.ProbeInputModel(implementation=str(higher.pk), args={}))

    async def test_inflight_cap_refuses_the_extra_call(self, agent_ws, authenticated_context):
        session = await open_agent(agent_ws, "guard-agent")
        impl = await build_implementation_for_agent(session.agent.pk, "guard-cap")

        info = _Info(authenticated_context)
        with override_settings(PROBE_MAX_INFLIGHT_PER_CALLER=1):
            await sync_to_async(probe_backend.probe)(info, inputs.ProbeInputModel(implementation=str(impl.pk), args={}))
            with pytest.raises(ValueError, match="in-flight"):
                await sync_to_async(probe_backend.probe)(info, inputs.ProbeInputModel(implementation=str(impl.pk), args={}))

    async def test_assign_request_with_call_parent_is_nacked(self, agent_ws, authenticated_context):
        session = await open_agent(agent_ws, "guard-agent")
        impl = await build_implementation_for_agent(session.agent.pk, "guard-parent")

        state = await sync_to_async(probe_backend.probe)(_Info(authenticated_context), inputs.ProbeInputModel(implementation=str(impl.pk), args={}))
        probe_id = state["id"]
        await session.receive(messages.Assign)

        await session.send(messages.AssignRequest(reference="sub-1", parent=probe_id, implementation=str(impl.pk), args={}))
        response = await session.receive(messages.AssignResponse)
        assert response.created is False
        assert response.task is None
        assert "cannot parent" in response.error

    async def test_lock_from_a_call_is_ignored_without_closing(self, agent_ws, authenticated_context):
        session = await open_agent(agent_ws, "guard-agent")
        impl = await build_implementation_for_agent(session.agent.pk, "guard-lock")

        state = await sync_to_async(probe_backend.probe)(_Info(authenticated_context), inputs.ProbeInputModel(implementation=str(impl.pk), args={}))
        probe_id = state["id"]
        await session.receive(messages.Assign)

        await session.send(messages.Lock(task=probe_id, key="shared-resource"))
        # the socket survives and keeps working: a terminal report still round-trips
        await session.send(messages.Completed(task=probe_id))
        ack = await session.receive(messages.EventAck)
        assert ack.task == probe_id
