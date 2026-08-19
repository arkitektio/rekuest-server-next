"""The probe GraphQL mutation layer, executed through the schema.

The other probe tests drive ``probe_backend`` directly, which let a broken
resolver-to-backend call slip through — this file covers the mutation/query surface
end-to-end via ``schema.execute``.
"""

import pytest

from facade.schema import schema

from tests.agent.helpers import open_agent
from tests.factories import build_implementation_for_agent

PROBE = """
    mutation Probe($input: ProbeInput!) {
        probe(input: $input) { id kind isDone agent implementation }
    }
"""

GET_PROBE = """
    query GetProbe($id: ID!) {
        probe(id: $id) { id kind isDone }
    }
"""


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
class TestProbeGraphQL:
    async def test_probe_mutation_and_query(self, agent_ws, authenticated_context):
        session = await open_agent(agent_ws, "gql-probe-agent")
        impl = await build_implementation_for_agent(session.agent.pk, "gql-probe")

        result = await schema.execute(PROBE, context_value=authenticated_context, variable_values={"input": {"implementation": str(impl.pk), "args": {}}})
        assert result.errors is None, result.errors
        probe = result.data["probe"]
        assert probe["id"].startswith("p-")
        assert probe["kind"] == "QUEUED"
        assert probe["isDone"] is False

        fetched = await schema.execute(GET_PROBE, context_value=authenticated_context, variable_values={"id": probe["id"]})
        assert fetched.errors is None, fetched.errors
        assert fetched.data["probe"]["id"] == probe["id"]
