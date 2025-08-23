import pytest
from facade.schema import schema
from kante.context import HttpContext
import pytest_asyncio


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_dataset_upper(db, authenticated_context: HttpContext):

    ensure_agent = """
        mutation EnsureAgent($input: AgentInput!) {
            ensureAgent(input: $input) {
                id
                instanceId
            }
        }
    """

    sub = await schema.execute(
        ensure_agent,
        context_value=authenticated_context,
        variable_values={
            "input": {
                "instanceId": "default"
            }
        }
    )

    assert sub.data, sub.errors

    assert sub.data["ensureAgent"]["instanceId"] == "default"
