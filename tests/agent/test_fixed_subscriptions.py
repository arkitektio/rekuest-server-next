"""Subscription feeds that were silently dead until the correctness round.

``newActions`` never yielded (the channel was built over the wrong pydantic model, so
every broadcast failed validation and was dropped) and ``implementations`` listened on a
group no producer targeted. These smokes pin the repaired plumbing end-to-end.
"""

import asyncio
import json

import pytest
from kante.testing.ws import GraphQLWebSocketTestClient

from rekuest.asgi import application
from tests.agent.helpers import open_agent
from tests.factories import build_implementation_for_agent

WARMUP = 1.0

NEW_ACTIONS = """
    subscription {
        newActions { id name }
    }
"""

IMPLEMENTATIONS = """
    subscription Implementations($agent: ID!) {
        implementations(agent: $agent) {
            create { id interface }
            update { id interface }
            delete
        }
    }
"""


async def _start(client, query, variables=None, op_id="1"):
    payload = {"query": query, "variables": variables or {}}
    await client.communicator.send_input({"type": "websocket.receive", "text": json.dumps({"id": op_id, "type": "start", "payload": payload})})


async def _recv(client, predicate, op_id="1", timeout=6):
    def match(msg):
        if msg.get("type") != "data" or msg.get("id") != op_id:
            return False
        payload = msg["payload"]
        if payload.get("errors"):
            raise AssertionError(f"subscription error: {payload['errors']}")
        return predicate(payload.get("data") or {})

    return await client.receive_until(match, timeout)


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
class TestRepairedSubscriptions:
    async def test_new_actions_yields_on_action_create(self, agent_ws):
        session = await open_agent(agent_ws, "subfix-agent", token="test")

        async with GraphQLWebSocketTestClient(application, connection_params={"token": "test"}) as client:
            await _start(client, NEW_ACTIONS)
            await asyncio.sleep(WARMUP)

            impl = await build_implementation_for_agent(session.agent.pk, "subfix-action")

            msg = await _recv(client, lambda d: d.get("newActions") is not None)
            node = msg["payload"]["data"]["newActions"]
            assert node["id"] == str(impl.action_id)

    async def test_implementations_feed_streams_create_and_delete(self, agent_ws):
        from asgiref.sync import sync_to_async

        session = await open_agent(agent_ws, "subfix-agent", token="test")

        async with GraphQLWebSocketTestClient(application, connection_params={"token": "test"}) as client:
            await _start(client, IMPLEMENTATIONS, {"agent": str(session.agent.pk)})
            await asyncio.sleep(WARMUP)

            impl = await build_implementation_for_agent(session.agent.pk, "subfix-impl")

            impl_pk = impl.pk  # .delete() nulls the instance pk
            created = await _recv(client, lambda d: (d.get("implementations") or {}).get("create") is not None)
            assert created["payload"]["data"]["implementations"]["create"]["id"] == str(impl_pk)

            await sync_to_async(impl.delete)()
            deleted = await _recv(client, lambda d: (d.get("implementations") or {}).get("delete") is not None)
            assert deleted["payload"]["data"]["implementations"]["delete"] == str(impl_pk)
