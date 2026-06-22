"""Full-stack caller-event return path (item 8).

When an agent is the *caller* of an assignation, events on that assignation are streamed
back to its own socket as ``Caller*`` messages. Here the registered agent is both the
executor (it reports a ProgressEvent) and the caller (the assignation's caller is its own
identity), so the progress it reports comes straight back to it as a ``CALLER_PROGRESS``.
"""

import pytest

from facade import messages
from facade.models import Agent

from tests.agent.helpers import RECEIVE_TIMEOUT, connect_and_register, send_message
from tests.factories import build_assignation, build_assignation_for_agent_caller


async def _recv_kind(communicator, kind, tries=10):
    """Read frames until one of ``kind`` arrives (skipping heartbeats/others)."""
    for _ in range(tries):
        frame = await communicator.receive_json_from(timeout=RECEIVE_TIMEOUT)
        if frame.get("type") == kind:
            return frame
    raise AssertionError(f"did not receive a {kind} frame")


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
class TestCallerEventReturn:
    async def test_caller_receives_progress_for_own_assignation(self, agent_ws):
        communicator, _ = await connect_and_register(agent_ws, "callerev-agent")
        agent = await Agent.objects.aget(hash="callerev-agent-hash")
        assignation = await build_assignation_for_agent_caller(agent.pk, "callerev")

        # Report progress as the executor …
        await send_message(communicator, messages.ProgressEvent(assignation=str(assignation.pk), progress=42, message="halfway"))

        # … and receive it back as the caller.
        frame = await _recv_kind(communicator, messages.ToAgentMessageType.CALLER_PROGRESS.value)
        assert frame["assignation"] == str(assignation.pk)
        assert frame["progress"] == 42 and frame["message"] == "halfway"
        assert frame["event"] and frame["seq"]  # dedup handle + ordering key present

        await communicator.disconnect()

    async def test_done_comes_back_as_caller_done(self, agent_ws):
        communicator, _ = await connect_and_register(agent_ws, "callerdone-agent")
        agent = await Agent.objects.aget(hash="callerdone-agent-hash")
        assignation = await build_assignation_for_agent_caller(agent.pk, "callerdone")

        await send_message(communicator, messages.DoneEvent(assignation=str(assignation.pk)))

        frame = await _recv_kind(communicator, messages.ToAgentMessageType.CALLER_DONE.value)
        assert frame["assignation"] == str(assignation.pk)
        await communicator.disconnect()

    async def test_only_own_caller_assignations_are_delivered(self, agent_ws):
        # Two assignations: one whose caller is us, one whose caller is a different identity.
        # Progress is reported on the OTHER first, then on OURS. Only ours must come back,
        # so the single CALLER_PROGRESS we receive must be for our assignation (progress 77),
        # never the other's (progress 10).
        communicator, _ = await connect_and_register(agent_ws, "calleriso-agent")
        agent = await Agent.objects.aget(hash="calleriso-agent-hash")
        mine = await build_assignation_for_agent_caller(agent.pk, "callermine")
        other = await build_assignation("callerother")  # caller = its own identity, not ours

        await send_message(communicator, messages.ProgressEvent(assignation=str(other.pk), progress=10))
        await send_message(communicator, messages.ProgressEvent(assignation=str(mine.pk), progress=77))

        frame = await _recv_kind(communicator, messages.ToAgentMessageType.CALLER_PROGRESS.value)
        assert frame["assignation"] == str(mine.pk) and frame["progress"] == 77

        await communicator.disconnect()
