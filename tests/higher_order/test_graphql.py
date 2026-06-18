"""GraphQL surface for higher-order implementations: the setHigherOrder mutation + exposure."""

import pytest
from asgiref.sync import sync_to_async
from kante.context import HttpContext

from facade.models import Action, Implementation
from facade.schema import schema

from tests.factories import create_agent_for_registry, create_registry_bundle

SET_HIGHER_ORDER = """
    mutation SetHO($input: SetHigherOrderInput!) {
        setHigherOrder(input: $input) {
            id
            higherOrderConfig
            higherOrderFor { id }
        }
    }
"""


def _build_impls(prefix, lower_kind="FUNCTION", higher_kind="FUNCTION"):
    user, _, org, registry = create_registry_bundle(prefix)
    agent = create_agent_for_registry(registry=registry, user=user, organization=org, prefix=prefix)

    lower_action = Action.objects.create(
        app=agent.app, key=f"{prefix}-l", version="1.0.0", name="l", description="l",
        hash=f"{prefix}-l-hash", organization=org, kind=lower_kind,
    )
    lower = Implementation.objects.create(release=agent.release, interface=f"{prefix}_l", action=lower_action, agent=agent, dynamic=False)

    higher_action = Action.objects.create(
        app=agent.app, key=f"{prefix}-h", version="1.0.0", name="h", description="h",
        hash=f"{prefix}-h-hash", organization=org, kind=higher_kind,
    )
    higher = Implementation.objects.create(release=agent.release, interface=f"{prefix}_h", action=higher_action, agent=agent, dynamic=False)

    return str(higher.id), str(lower.id)


build_impls = sync_to_async(_build_impls)


def _build_cross_agent_impls(prefix):
    """Build a wrapper and a lower impl on two DIFFERENT agents (different registries)."""
    h_user, _, h_org, h_registry = create_registry_bundle(f"{prefix}-h")
    h_agent = create_agent_for_registry(registry=h_registry, user=h_user, organization=h_org, prefix=f"{prefix}-h")
    higher_action = Action.objects.create(
        app=h_agent.app, key=f"{prefix}-h", version="1.0.0", name="h", description="h",
        hash=f"{prefix}-h-hash", organization=h_org, kind="FUNCTION",
    )
    higher = Implementation.objects.create(release=h_agent.release, interface=f"{prefix}_h", action=higher_action, agent=h_agent, dynamic=False)

    l_user, _, l_org, l_registry = create_registry_bundle(f"{prefix}-l")
    l_agent = create_agent_for_registry(registry=l_registry, user=l_user, organization=l_org, prefix=f"{prefix}-l")
    lower_action = Action.objects.create(
        app=l_agent.app, key=f"{prefix}-l", version="1.0.0", name="l", description="l",
        hash=f"{prefix}-l-hash", organization=l_org, kind="FUNCTION",
    )
    lower = Implementation.objects.create(release=l_agent.release, interface=f"{prefix}_l", action=lower_action, agent=l_agent, dynamic=False)

    return str(higher.id), str(lower.id)


build_cross_agent_impls = sync_to_async(_build_cross_agent_impls)


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
class TestSetHigherOrder:
    async def test_link_round_trips(self, authenticated_context: HttpContext):
        higher_id, lower_id = await build_impls("ho-ok")

        result = await schema.execute(
            SET_HIGHER_ORDER,
            context_value=authenticated_context,
            variable_values={"input": {"implementation": higher_id, "lowerImplementation": lower_id, "config": {"args_key": "args"}}},
        )

        assert result.data is not None, f"Errors: {result.errors}"
        payload = result.data["setHigherOrder"]
        assert payload["id"] == higher_id
        assert payload["higherOrderFor"]["id"] == lower_id
        assert payload["higherOrderConfig"] == {"args_key": "args"}

    async def test_self_wrap_is_rejected(self, authenticated_context: HttpContext):
        higher_id, _ = await build_impls("ho-self")

        result = await schema.execute(
            SET_HIGHER_ORDER,
            context_value=authenticated_context,
            variable_values={"input": {"implementation": higher_id, "lowerImplementation": higher_id}},
        )

        assert result.errors is not None

    async def test_kind_mismatch_is_rejected(self, authenticated_context: HttpContext):
        # FUNCTION wrapper over a GENERATOR lower → rejected at link time.
        higher_id, lower_id = await build_impls("ho-kind", lower_kind="GENERATOR", higher_kind="FUNCTION")

        result = await schema.execute(
            SET_HIGHER_ORDER,
            context_value=authenticated_context,
            variable_values={"input": {"implementation": higher_id, "lowerImplementation": lower_id}},
        )

        assert result.errors is not None

    async def test_cross_agent_link_is_rejected(self, authenticated_context: HttpContext):
        # Wrapper and lower on different agents → rejected: a wrapper must be co-located
        # with the lower implementation it wraps.
        higher_id, lower_id = await build_cross_agent_impls("ho-xagent")

        result = await schema.execute(
            SET_HIGHER_ORDER,
            context_value=authenticated_context,
            variable_values={"input": {"implementation": higher_id, "lowerImplementation": lower_id}},
        )

        assert result.errors is not None
