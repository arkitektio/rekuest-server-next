"""The ``probeEvents`` subscription: payload-carrying, caller-scoped, snapshot-first.

Mirrors the mechanics of ``tests/agent/test_graphql_subscriptions.py``: the GraphQL
websocket authenticates with the same static ``test`` token identity the seeded agent
derives, so the ws client IS the probe's caller when the probe is created with
``CallerContext.from_agent``.
"""

import asyncio
import json

import pytest
from asgiref.sync import sync_to_async
from kante.testing.ws import GraphQLWebSocketTestClient

from facade import inputs, messages
from facade.caller_context import CallerContext
from facade.probes.backend import probe_backend
from rekuest.asgi import application

from tests.agent.helpers import open_agent
from tests.factories import build_implementation_for_agent

WARMUP = 1.0

PROBE_EVENTS = """
    subscription ProbeEvents($probe: ID!) {
        probeEvents(probe: $probe) { probe kind seq returns message }
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
class TestProbeEventsSubscription:
    async def test_snapshot_then_live_stream(self, agent_ws, backend_stack):
        session = await open_agent(agent_ws, "sub-probe-agent", token="test")
        impl = await build_implementation_for_agent(session.agent.pk, "sub-probe")

        ctx = CallerContext.from_agent(session.agent)
        state = await sync_to_async(probe_backend.probe)(ctx, inputs.ProbeInputModel(implementation=str(impl.pk), args={}))
        probe_id = state["id"]
        await session.receive(messages.Assign)

        # events BEFORE anyone subscribes — the snapshot must cover them
        await session.send(messages.Started(task=probe_id))
        await session.receive(messages.EventAck)
        await session.send(messages.Yield(task=probe_id, returns={"out": 7}))
        await asyncio.sleep(0.3)  # let the fire-and-forget yield land in redis

        async with GraphQLWebSocketTestClient(application, connection_params={"token": "test"}) as client:
            await _start(client, PROBE_EVENTS, {"probe": probe_id})

            snapshot = await _recv(client, lambda d: (d.get("probeEvents") or {}).get("seq") is not None)
            node = snapshot["payload"]["data"]["probeEvents"]
            assert node["probe"] == probe_id
            assert node["kind"] == "YIELD"
            assert node["seq"] == 2
            assert node["returns"] == {"out": 7}

            await asyncio.sleep(WARMUP)  # join the group before the live event fires

            await session.send(messages.Completed(task=probe_id))
            live = await _recv(client, lambda d: (d.get("probeEvents") or {}).get("kind") == "COMPLETED")
            node = live["payload"]["data"]["probeEvents"]
            assert node["seq"] == 3

    async def test_unknown_probe_errors(self, agent_ws, backend_stack):
        await open_agent(agent_ws, "sub-probe-agent", token="test")

        async with GraphQLWebSocketTestClient(application, connection_params={"token": "test"}) as client:
            await _start(client, PROBE_EVENTS, {"probe": "p-doesnotexist"})

            # the resolver raises before its first yield → an error frame, never data
            frame = await client.receive_until(lambda msg: msg.get("type") in ("error", "data"), 6)
            if frame["type"] == "data":
                assert frame["payload"].get("errors"), frame
            else:
                assert "Unknown or expired" in json.dumps(frame["payload"])
