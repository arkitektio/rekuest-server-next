"""Full-stack agent state events: patches, snapshots and session init."""

import pytest

from facade import messages
from facade.models import Patch, Snapshot

from tests.agent.helpers import open_agent
from tests.factories import build_state_for_agent


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
class TestAgentStateEvents:
    async def test_state_patch_persists(self, agent_ws):
        session = await open_agent(agent_ws, "patch-agent")
        await build_state_for_agent(session.agent_pk, interface="counter", prefix="patch")

        await session.send(
            messages.StatePatchEvent(
                session_id="session-1", global_rev=1, state_name="counter", ts=0.0,
                op="replace", path="/value", value=5, old_value=None, correlation_id=None,
            )
        )

        await session.disconnect()
        patch = await Patch.objects.filter(agent_id=session.agent_pk, interface="counter").aget()
        assert patch.op == "replace"
        assert patch.path == "/value"
        assert patch.value == 5
        assert patch.global_rev == 1

    async def test_state_snapshot_persists(self, agent_ws):
        session = await open_agent(agent_ws, "snapshot-agent")
        await build_state_for_agent(session.agent_pk, interface="counter", prefix="snapshot")

        await session.send(messages.StateSnapshotEvent(session_id="session-2", global_rev=3, snapshots={"counter": {"value": 9}}))

        await session.disconnect()
        snapshot = await Snapshot.objects.filter(agent_id=session.agent_pk, global_rev=3).aget()
        assert snapshot.value == {"value": 9}

    async def test_session_init_creates_snapshots(self, agent_ws):
        session = await open_agent(agent_ws, "session-agent")
        await build_state_for_agent(session.agent_pk, interface="counter", prefix="session")

        await session.send(messages.SessionInitMessage(session_id="session-3", states={"counter": {"value": 0}}))

        await session.disconnect()
        snapshot = await Snapshot.objects.filter(agent_id=session.agent_pk).aget()
        assert snapshot.value == {"value": 0}
