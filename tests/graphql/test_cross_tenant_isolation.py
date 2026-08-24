"""Cross-tenant isolation: a caller in org A must not see org B's rows.

The audit found that scoping exists on only 4 of ~35 auto-generated types (via
``facade.types.base.build_prescoped_queryset``), so most of the GraphQL surface returns rows
from every organization to any authenticated user. Nothing in the suite asserted otherwise —
before this file there were exactly two negative-authz assertions in the whole test suite, both
about probes.

``test_actions_are_scoped_to_the_callers_organization`` is the control: ``Action`` *is* one of
the four scoped types, so it passes and proves the harness itself is sound. The remaining tests
exercise unscoped types and are expected to FAIL until scoping is added — they are the
executable statement of the finding.
"""

import pytest
from asgiref.sync import sync_to_async
from authentikate.models import Membership
from kante.context import HttpContext, UniversalRequest
from strawberry.http.temporal_response import TemporalResponse

from facade.schema import schema
from tests.factories import (
    _build_state_for_agent,
    create_action_for_organization,
    create_agent_for_registry,
    create_registry_bundle,
)


def _context_for(user, client, org):
    """An HttpContext authenticated as ``user`` acting in ``org`` (mirrors conftest)."""
    membership, _ = Membership.objects.get_or_create(user=user, organization=org)
    request = UniversalRequest(
        _extensions={"token": "test"},
        _client=client,  # type: ignore[arg-type]
        _user=user,  # type: ignore[arg-type]
        _organization=org,  # type: ignore[arg-type]
    )
    request.set_membership(membership)  # type: ignore[attr-defined]
    return HttpContext(request=request, response=TemporalResponse(), headers={"Authorization": "Bearer test"}, type="http")


@sync_to_async
def _seed_two_tenants(prefix):
    """Two complete, independent tenants, each with an agent, a state and an action."""
    tenants = {}
    for side in ("a", "b"):
        user, client, org, caller = create_registry_bundle(f"{prefix}-{side}")
        agent = create_agent_for_registry(caller, user, org, f"{prefix}-{side}")
        state = _build_state_for_agent(agent.pk, f"{prefix}-{side}-iface", f"{prefix}-{side}")
        action = create_action_for_organization(org, f"{prefix}-{side}-act")
        tenants[side] = {
            "context": _context_for(user, client, org),
            "org": org,
            "agent": agent,
            "state": state,
            "action": action,
        }
    return tenants


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
class TestCrossTenantIsolation:
    async def test_actions_are_scoped_to_the_callers_organization(self, authenticated_context):
        """Control: Action has a get_queryset scope, so this must pass.

        ``authenticated_context`` is requested only to pull in the ``db`` + ``backend_stack``
        session setup; each test builds its own per-tenant contexts.
        """
        t = await _seed_two_tenants("xt-actions")

        result = await schema.execute("query { actions { id } }", context_value=t["a"]["context"])

        assert not result.errors, result.errors
        returned = {row["id"] for row in result.data["actions"]}
        assert str(t["b"]["action"].id) not in returned, "org A can see org B's Action"

    async def test_states_are_scoped_to_the_callers_organization(self, authenticated_context):
        """State has no get_queryset — org A currently receives org B's states."""
        t = await _seed_two_tenants("xt-states")

        result = await schema.execute("query { states { id interface } }", context_value=t["a"]["context"])

        assert not result.errors, result.errors
        returned = {row["id"] for row in result.data["states"]}
        assert str(t["b"]["state"].id) not in returned, "org A can see org B's State"

    async def test_single_state_lookup_is_scoped(self, authenticated_context):
        """facade/schema.py:104 resolves State.objects.get(id=id) with no organization filter."""
        t = await _seed_two_tenants("xt-state-by-id")

        result = await schema.execute(
            "query Q($id: ID!) { state(id: $id) { id interface } }",
            context_value=t["a"]["context"],
            variable_values={"id": str(t["b"]["state"].id)},
        )

        assert result.errors or result.data.get("state") is None, "org A fetched org B's State by id"
