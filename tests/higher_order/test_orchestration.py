"""Full-stack higher-order orchestration: assign H -> child L -> unfold returns onto H.

Drives the real agent socket (the lower agent) plus the server-side ``assign`` /
``persist_backend`` paths against real Postgres + Redis (dokker fixtures).
"""

import pytest
from asgiref.sync import sync_to_async

from facade import inputs, messages
from facade.backend import controll_backend
from facade.models import Action, Agent, Assignation, AssignationEvent, Implementation

from tests.agent.helpers import RECEIVE_TIMEOUT, register, send_message
from tests.factories import seed_agent

HIGHER_ORDER_CONFIG = {"bound": {"model": "resnet50"}, "args_key": "args", "return_map": {"result": "out"}}


class _Info:
    """Minimal stand-in for the Strawberry ``Info`` the backend reads (`.context.request`)."""

    def __init__(self, context):
        self.context = context


def _build_hoi_graph(agent_pk):
    """On ``agent``: a lower action+impl (L) and a higher-order impl (H) wrapping it."""
    agent = Agent.objects.get(pk=agent_pk)

    lower_action = Action.objects.create(
        app=agent.app, key="lower-key", version="1.0.0", name="lower action",
        description="lower", hash="lower-action-hash", organization=agent.organization,
    )
    lower_impl = Implementation.objects.create(
        release=agent.release, interface="lower_fn", action=lower_action, agent=agent, dynamic=False,
    )

    higher_action = Action.objects.create(
        app=agent.app, key="higher-key", version="1.0.0", name="higher action",
        description="higher", hash="higher-action-hash", organization=agent.organization,
    )
    higher_impl = Implementation.objects.create(
        release=agent.release, interface="higher_fn", action=higher_action, agent=agent, dynamic=False,
        higher_order_for=lower_impl, higher_order_config=HIGHER_ORDER_CONFIG,
    )
    return higher_impl, lower_impl


build_hoi_graph = sync_to_async(_build_hoi_graph)


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
class TestHigherOrderOrchestration:
    async def test_assign_remaps_args_and_unfolds_returns(self, agent_ws, authenticated_context):
        agent = await seed_agent("hoi-agent")
        higher_impl, lower_impl = await build_hoi_graph(agent.pk)

        # Connect the lower agent (marks it connected so the lower action resolves).
        communicator = await agent_ws()
        await register(communicator, instance_id="hoi-agent")

        info = _Info(authenticated_context)

        # Assign the higher-order implementation with the caller's typed args.
        higher_assignation = await sync_to_async(controll_backend.assign)(
            info, inputs.AssignInputModel(implementation=str(higher_impl.pk), args={"x": 1})
        )

        # The lower agent receives a normal Assign for the child, with remapped args.
        received = await communicator.receive_json_from(timeout=RECEIVE_TIMEOUT)
        assert received["type"] == messages.ToAgentMessageType.ASSIGN.value
        assert received["args"] == {"model": "resnet50", "args": {"x": 1}}
        child_id = received["assignation"]

        # The child is a child of the (virtual) higher assignation and runs on the lower agent.
        child = await Assignation.objects.aget(pk=child_id)
        assert str(child.parent_id) == str(higher_assignation.pk)
        assert str(child.agent_id) == str(agent.pk)

        # Drive the lower agent: yield then done.
        await send_message(communicator, messages.YieldEvent(assignation=child_id, returns={"out": 42}))
        await send_message(communicator, messages.DoneEvent(assignation=child_id))
        await communicator.disconnect()

        # The wrapper assignation sees the UNFOLDED yield (mapped via return_map) + delegated_to.
        higher_yield = await AssignationEvent.objects.filter(
            assignation_id=higher_assignation.pk, kind="YIELD"
        ).aget()
        assert higher_yield.returns == {"result": 42}
        assert str(higher_yield.delegated_to_id) == str(child_id)

        # Done propagates to the wrapper.
        assert await AssignationEvent.objects.filter(assignation_id=higher_assignation.pk, kind="DONE").aexists()
        refreshed = await Assignation.objects.aget(pk=higher_assignation.pk)
        assert refreshed.is_done is True

    async def test_assign_fails_when_no_lower_agent_connected(self, agent_ws, authenticated_context):
        # Seed + build the graph but DO NOT connect the agent → lower action has no live agent.
        agent = await seed_agent("hoi-agent-offline")
        higher_impl, _ = await build_hoi_graph(agent.pk)

        info = _Info(authenticated_context)

        with pytest.raises(ValueError):
            await sync_to_async(controll_backend.assign)(
                info, inputs.AssignInputModel(implementation=str(higher_impl.pk), args={"x": 1})
            )
