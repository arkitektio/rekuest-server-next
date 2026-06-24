"""GraphQL subscription surface — the slim, non-traversable change feeds, observed over a real socket.

The mirror of ``test_cross_agent`` but on the GraphQL side: a client opens a subscription over the
GraphQL websocket (authenticated via ``connection_params`` token, the same static identities the
agent tests use) and asserts it receives the right *slim* events under the right scope:

- ``mytasks``  — root tasks (+ their events) the calling client originated; child tasks are filtered out.
- ``tasks``    — root task changes across the whole organization (a different client, same org, sees them).
- ``childTasks(id)`` — the whole descendant subtree of one task (direct children AND deeper ones,
  via the parent/root fan-out).
- ``agents``   — slim agent changes across the organization (create/update/delete, FKs as bare ids).

Sequencing note: the test channel layer is in-memory, so a broadcast only reaches a subscription
that has *already joined* its group. Every test therefore does ``_start`` → ``sleep(WARMUP)`` →
trigger, so the resolver has joined before we save the row that fans out.
"""

import asyncio
import json

import pytest
from kante.testing.ws import GraphQLWebSocketTestClient

from facade import messages
from rekuest.asgi import application
from tests.agent.helpers import open_agent
from tests.factories import (
    build_implementation_for_agent,
    build_task_event,
    build_task_for_agent_caller,
    seed_agent,
    touch_agent,
)

WARMUP = 1.0  # let the resolver run aget_or_create + join its channel group before we trigger

MYTASKS = """
    subscription {
        mytasks {
            create { id root parent action isDone latestEventKind }
            event { task kind }
        }
    }
"""

TASKS = """
    subscription {
        tasks {
            create { id root parent }
            event { task kind }
        }
    }
"""

CHILD_TASKS = """
    subscription ChildTasks($id: ID!) {
        childTasks(id: $id) {
            create { id root parent }
            update { id root parent }
        }
    }
"""

AGENTS = """
    subscription {
        agents {
            create { id name kind connected client organization }
            update { id connected }
            delete
        }
    }
"""


async def _start(client, query, variables=None, op_id="1"):
    """Send a graphql-ws ``start`` frame (lets us control timing vs the high-level subscribe())."""
    payload = {"query": query}
    if variables:
        payload["variables"] = variables
    await client.communicator.send_input(
        {"type": "websocket.receive", "text": json.dumps({"id": op_id, "type": "start", "payload": payload})}
    )


def _is_data(msg, op_id="1"):
    return msg.get("type") == "data" and msg.get("id") == op_id


async def _recv(client, predicate, op_id="1", timeout=6):
    """Return the first ``data`` frame whose payload satisfies ``predicate`` (raises on GraphQL errors)."""

    def match(msg):
        if not _is_data(msg, op_id):
            return False
        payload = msg["payload"]
        if payload.get("errors"):
            raise AssertionError(f"subscription error: {payload['errors']}")
        return predicate(payload.get("data") or {})

    return await client.receive_until(match, timeout)


async def _stop(client, op_id="1"):
    """Cleanly stop the subscription so the server unwinds it in its own context (no teardown noise)."""
    await client.communicator.send_input(
        {"type": "websocket.receive", "text": json.dumps({"id": op_id, "type": "stop"})}
    )
    await asyncio.sleep(0.2)


def _create(data, field="mytasks"):
    node = data.get(field) or {}
    return node.get("create")


def _event(data, field="mytasks"):
    node = data.get(field) or {}
    return node.get("event")


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
class TestTaskSubscriptions:
    async def test_mytasks_smoke_authenticates(self, backend_stack):
        # Canary: proves connection_params auth reaches the resolver AND the slim shape is non-traversable.
        agent = await seed_agent("sub-smoke", token="test")

        async with GraphQLWebSocketTestClient(application, connection_params={"token": "test"}) as client:
            await _start(client, MYTASKS)
            await asyncio.sleep(WARMUP)

            root = await build_task_for_agent_caller(agent.pk, "sub-smoke")

            msg = await _recv(client, lambda d: _create(d) is not None)
            create = _create(msg["payload"]["data"])
            assert create["id"] == str(root.id)
            assert create["root"] is None  # it IS the root
            assert isinstance(create["action"], str)  # a bare id — no relation traversal
            await _stop(client)

    async def test_mytasks_streams_create_then_event(self, backend_stack):
        agent = await seed_agent("sub-stream", token="test")

        async with GraphQLWebSocketTestClient(application, connection_params={"token": "test"}) as client:
            await _start(client, MYTASKS)
            await asyncio.sleep(WARMUP)

            root = await build_task_for_agent_caller(agent.pk, "sub-stream")
            create = await _recv(client, lambda d: _create(d) is not None)
            assert _create(create["payload"]["data"])["id"] == str(root.id)

            await build_task_event(root.pk, kind="COMPLETED")
            event = await _recv(client, lambda d: _event(d) is not None)
            ev = _event(event["payload"]["data"])
            assert ev["task"] == str(root.id)
            assert ev["kind"] == "COMPLETED"
            await _stop(client)

    async def test_mytasks_ignores_child_tasks(self, backend_stack):
        # Root-only: a child task must not reach the caller feed. We assert it negatively via a
        # sentinel — the child is fanned out first, then a fresh root; the next delivered message
        # being the *root* (not the child) proves the child was filtered at the source.
        agent = await seed_agent("sub-rootonly", token="test")
        root = await build_task_for_agent_caller(agent.pk, "sub-rootonly-root")

        async with GraphQLWebSocketTestClient(application, connection_params={"token": "test"}) as client:
            await _start(client, MYTASKS)
            await asyncio.sleep(WARMUP)

            await build_task_for_agent_caller(agent.pk, "sub-rootonly-child", parent=root, root=root)
            sentinel = await build_task_for_agent_caller(agent.pk, "sub-rootonly-sentinel")

            msg = await _recv(client, lambda d: _create(d) is not None)
            assert _create(msg["payload"]["data"])["id"] == str(sentinel.id)
            await _stop(client)

    async def test_mytasks_is_caller_scoped(self, backend_stack):
        # A root task owned by a DIFFERENT client (same org) must not reach this caller's feed.
        # Same sentinel technique: the other client's root, then our own; we must receive only ours.
        me = await seed_agent("sub-scope-self", token="test")
        other = await seed_agent("sub-scope-other", token="test2")

        async with GraphQLWebSocketTestClient(application, connection_params={"token": "test"}) as client:
            await _start(client, MYTASKS)
            await asyncio.sleep(WARMUP)

            await build_task_for_agent_caller(other.pk, "sub-scope-other-task")
            sentinel = await build_task_for_agent_caller(me.pk, "sub-scope-self-task")

            msg = await _recv(client, lambda d: _create(d) is not None)
            assert _create(msg["payload"]["data"])["id"] == str(sentinel.id)
            await _stop(client)

    async def test_tasks_is_org_wide(self, backend_stack):
        # The org-wide feed: a client (test2) sees a root task originated by another client (test) in its org.
        agent = await seed_agent("sub-org-owner", token="test")

        async with GraphQLWebSocketTestClient(application, connection_params={"token": "test2"}) as client:
            await _start(client, TASKS)
            await asyncio.sleep(WARMUP)

            root = await build_task_for_agent_caller(agent.pk, "sub-org-task")
            msg = await _recv(client, lambda d: _create(d, "tasks") is not None)
            assert _create(msg["payload"]["data"], "tasks")["id"] == str(root.id)
            await _stop(client)

    async def test_child_tasks_sees_whole_subtree(self, backend_stack):
        # The detail feed fans out to BOTH parent and root, so a sub on the root sees deep descendants.
        agent = await seed_agent("sub-subtree", token="test")
        root = await build_task_for_agent_caller(agent.pk, "sub-subtree-root")

        async with GraphQLWebSocketTestClient(application, connection_params={"token": "test"}) as client:
            await _start(client, CHILD_TASKS, variables={"id": str(root.id)})
            await asyncio.sleep(WARMUP)

            child = await build_task_for_agent_caller(agent.pk, "sub-subtree-child", parent=root, root=root)
            msg = await _recv(client, lambda d: _create(d, "childTasks") is not None)
            assert _create(msg["payload"]["data"], "childTasks")["id"] == str(child.id)

            grandchild = await build_task_for_agent_caller(agent.pk, "sub-subtree-gc", parent=child, root=root)
            msg = await _recv(client, lambda d: _create(d, "childTasks") is not None)
            created = _create(msg["payload"]["data"], "childTasks")
            assert created["id"] == str(grandchild.id)
            assert created["parent"] == str(child.id)  # deep descendant — reaches us via the root fan-out
            assert created["root"] == str(root.id)
            await _stop(client)

    async def test_cross_agent_root_task_visible_on_mytasks(self, agent_ws):
        # Headline: the cross-agent dispatch flow, observed over the GraphQL mytasks subscription.
        executor = await open_agent(agent_ws, "sub-x-exec", token="test2")
        impl = await build_implementation_for_agent(executor.agent_pk, "subx")
        caller = await open_agent(agent_ws, "sub-x-caller")  # default token "test"

        async with GraphQLWebSocketTestClient(application, connection_params={"token": "test"}) as client:
            await _start(client, MYTASKS)
            await asyncio.sleep(WARMUP)

            await caller.send(messages.AssignRequest(reference="subx-1", implementation=str(impl.pk), args={}))
            result = await caller.receive(messages.AssignResponse)
            assign = await executor.receive(messages.Assign)

            create = await _recv(client, lambda d: (_create(d) or {}).get("id") == result.task)
            assert _create(create["payload"]["data"])["root"] is None

            await executor.send(messages.Completed(task=assign.task))
            await caller.receive(messages.CompletedEvent)

            done = await _recv(client, lambda d: (_event(d) or {}).get("kind") == "COMPLETED")
            assert _event(done["payload"]["data"])["task"] == result.task
            await _stop(client)

            await caller.disconnect()
            await executor.disconnect()

    async def test_agents_emits_slim_create_and_update(self, backend_stack):
        # The agents feed carries slim, non-traversable agent snapshots (FKs as bare ids).
        async with GraphQLWebSocketTestClient(application, connection_params={"token": "test"}) as client:
            await _start(client, AGENTS)
            await asyncio.sleep(WARMUP)

            agent = await seed_agent("agent-sub-target", token="test")  # create → fan-out
            msg = await _recv(client, lambda d: _create(d, "agents") is not None)
            create = _create(msg["payload"]["data"], "agents")
            assert create["id"] == str(agent.pk)
            assert isinstance(create["client"], str)  # a bare id — no relation traversal
            assert isinstance(create["organization"], str)
            assert create["kind"] in ("WEBSOCKET", "WEBHOOK")

            await touch_agent(agent.pk)  # re-save → update
            msg = await _recv(client, lambda d: (d.get("agents") or {}).get("update") is not None)
            assert msg["payload"]["data"]["agents"]["update"]["id"] == str(agent.pk)
            await _stop(client)
