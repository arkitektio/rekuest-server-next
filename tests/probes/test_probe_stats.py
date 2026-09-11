"""probeStats: live counts from the TTL keyspace.

Everything here goes through ``schema.execute``: GraphQL resolvers run under the
AuthExtension, which resolves identity from the Bearer token — so the probes must be
created through the same layer for the inflight counter to be scoped to the same caller.
"""

import pytest

from facade import messages
from facade.probes.store import get_probe_store
from facade.schema import schema

from tests.agent.helpers import open_agent
from tests.factories import build_implementation_for_agent

PROBE = """
    mutation Probe($input: ProbeInput!) {
        probe(input: $input) { id }
    }
"""

PROBE_STATS = """
    query { probeStats { totalLive myInflight maxInflight } }
"""


async def _fire(authenticated_context, impl_pk):
    result = await schema.execute(PROBE, context_value=authenticated_context, variable_values={"input": {"implementation": str(impl_pk), "args": {}}})
    assert result.errors is None, result.errors
    return result.data["probe"]["id"]


async def _stats(authenticated_context):
    result = await schema.execute(PROBE_STATS, context_value=authenticated_context)
    assert result.errors is None, result.errors
    return result.data["probeStats"]


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
class TestProbeStats:
    async def test_counts_track_lifecycle(self, agent_ws, authenticated_context):
        session = await open_agent(agent_ws, "stats-agent")
        impl = await build_implementation_for_agent(session.agent.pk, "stats")

        first = await _fire(authenticated_context, impl.pk)
        second = await _fire(authenticated_context, impl.pk)
        await session.receive(messages.Assign)
        await session.receive(messages.Assign)

        stats = await _stats(authenticated_context)
        assert stats["totalLive"] == 2
        assert stats["myInflight"] == 2
        assert stats["maxInflight"] > 0

        # a terminal report frees the inflight slot (the hash lingers, so totalLive stays)
        await session.send(messages.Completed(task=first))
        await session.receive(messages.EventAck)

        stats = await _stats(authenticated_context)
        assert stats["myInflight"] == 1
        assert stats["totalLive"] == 2  # terminal probe lingers under its reduced TTL

        assert (await get_probe_store().aget(second))["kind"] == "QUEUED"
