"""Full-stack provenance dispatch: a real top-level ``assign`` attaches a token.

Drives the server-side ``assign`` path against real Postgres + Redis (dokker
fixtures) and the live agent socket, asserting that the provenance token rides
the Assign message the agent receives — and that ``needs_token=False`` opts out.
"""

import pytest
from asgiref.sync import sync_to_async
from joserfc import jwt
from joserfc.jwk import KeySet

from facade import inputs, messages
from facade.backend import controll_backend
from facade.models import Action, Agent, Implementation
from facade.provenance import canonical, keys

from tests.agent.helpers import RECEIVE_TIMEOUT, register
from tests.factories import seed_agent


class _Info:
    """Minimal stand-in for the Strawberry ``Info`` the backend reads."""

    def __init__(self, context):
        self.context = context


def _decode(token):
    return jwt.decode(token, KeySet([keys.get_public_key()]), algorithms=keys.ALGORITHMS)


def _build_impl(agent_pk, *, needs_token=True):
    agent = Agent.objects.get(pk=agent_pk)
    action = Action.objects.create(
        app=agent.app, key="prov-key", version="1.0.0", name="prov action",
        description="prov", hash="prov-action-hash", organization=agent.organization,
    )
    return Implementation.objects.create(
        release=agent.release, interface="prov_fn", action=action, agent=agent,
        dynamic=False, needs_token=needs_token,
    )


build_impl = sync_to_async(_build_impl)


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
class TestProvenanceDispatch:
    async def test_top_level_assign_attaches_token(self, agent_ws, authenticated_context):
        agent = await seed_agent("prov-agent")
        impl = await build_impl(agent.pk, needs_token=True)

        communicator = await agent_ws()
        await register(communicator, instance_id="prov-agent")

        info = _Info(authenticated_context)
        task = await sync_to_async(controll_backend.assign)(
            info, inputs.AssignInputModel(implementation=str(impl.pk), args={"x": 1})
        )

        received = await communicator.receive_json_from(timeout=RECEIVE_TIMEOUT)
        await communicator.disconnect()

        assert received["type"] == messages.ToAgentMessageType.ASSIGN.value
        assert received["token"] is not None

        decoded = _decode(received["token"])
        assert decoded.header["alg"] == "EdDSA"
        claims = decoded.claims
        assert claims["tsk"] == str(task.pk)
        assert claims["rtk"] == str(task.pk)
        assert claims["ptk"] is None
        # The seeded caller's sub (static test token) is the human root.
        assert claims["sub"] == "1"
        assert claims["rcb"] == "1"
        assert claims["ahs"] == canonical.args_hash({"x": 1})
        assert isinstance(claims["aud"], list)

    async def test_needs_token_false_dispatches_without_token(self, agent_ws, authenticated_context):
        agent = await seed_agent("prov-agent-2")
        impl = await build_impl(agent.pk, needs_token=False)

        communicator = await agent_ws()
        await register(communicator, instance_id="prov-agent-2")

        info = _Info(authenticated_context)
        await sync_to_async(controll_backend.assign)(
            info, inputs.AssignInputModel(implementation=str(impl.pk), args={"x": 1})
        )

        received = await communicator.receive_json_from(timeout=RECEIVE_TIMEOUT)
        await communicator.disconnect()

        assert received["type"] == messages.ToAgentMessageType.ASSIGN.value
        assert received["token"] is None
