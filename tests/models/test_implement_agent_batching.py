"""Query-count regression guard for the ``implement_agent`` reconnect fast path.

A reconnecting agent re-declares an unchanged implementation set (same definition hashes).
The mutation prefetches the agent's Actions and Implementations in two queries and passes
the maps into ``_create_implementation``, so the per-implementation cost on the fast path
is a couple of statements (relational-state probe + implementation save + savepoints), not
a fresh lookup pair each. This pins the bound so a reintroduced N+1 fails loudly.
"""

from types import SimpleNamespace

import pytest
from authentikate.models import App, Release
from django.db import connection
from django.test.utils import CaptureQueriesContext

from facade import models
from facade.mutations.agent import ImplementAgentInputModel, implement_agent

from tests.factories import create_registry_bundle


def _implementation(interface):
    return {
        "interface": interface,
        "definition": {
            "key": interface,
            "version": "1",
            "name": interface.title(),
            "kind": "FUNCTION",
            "args": [
                {
                    "key": "image",
                    "kind": "STRUCTURE",
                    "identifier": "@mikro/image",
                    "nullable": False,
                    "requires": [{"key": "axes", "operator": "EQUALS", "value": "c"}],
                }
            ],
            "returns": [],
        },
    }


@pytest.mark.django_db
def test_reconnect_fast_path_query_count_is_bounded():
    user, client, org, _ = create_registry_bundle("impl-batch")
    client.release = Release.objects.create(app=App.objects.create(identifier="impl-batch-app"), version="1.0.0")
    client.save()

    payload = ImplementAgentInputModel.model_validate({"implementations": [_implementation(f"iface_{i}") for i in range(3)]})
    fake_input = SimpleNamespace(to_pydantic=lambda: payload)
    info = SimpleNamespace(context=SimpleNamespace(request=SimpleNamespace(client=client, user=user, organization=org)))

    # Cold registration creates agent, actions, ports, catalog entities, implementations.
    implement_agent(info, fake_input)
    assert models.Implementation.objects.count() == 3

    # Reconnect with the identical declaration: the unchanged-hash fast path plus the batch
    # prefetch maps. Budget: agent upsert (2) + prefetches (2) + per implementation a
    # relational-state probe, an UPDATE and a savepoint pair (~4 × 3) + the two reap
    # queries + shelve/lock bookkeeping. Well under the ~2 lookups + rebuild per
    # implementation the unbatched path would add.
    with CaptureQueriesContext(connection) as ctx:
        implement_agent(info, fake_input)

    assert models.Implementation.objects.count() == 3
    assert len(ctx) <= 25, f"reconnect fast path issued {len(ctx)} queries:\n" + "\n".join(q["sql"][:120] for q in ctx.captured_queries)
