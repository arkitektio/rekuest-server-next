"""Full-stack caller-assign over the agent socket (item 4).

A participant originates work via ``CallerAssign`` and gets a ``CallerAssignResult`` back.
Here the registered agent assigns to its own implementation, so it both originates the work
(caller) and receives the ``ASSIGN`` command (executor). Idempotency: resending the same
``reference`` returns the same assignation with ``created=False``.
"""

import pytest

from facade import messages
from facade.models import Agent, Assignation

from tests.agent.helpers import RECEIVE_TIMEOUT, connect_and_register, send_message
from tests.factories import build_implementation_for_agent


async def _recv_kind(communicator, kind, tries=12):
    for _ in range(tries):
        frame = await communicator.receive_json_from(timeout=RECEIVE_TIMEOUT)
        if frame.get("type") == kind:
            return frame
    raise AssertionError(f"did not receive a {kind} frame")


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
class TestCallerAssign:
    async def test_caller_assign_creates_then_is_idempotent(self, agent_ws):
        communicator, _ = await connect_and_register(agent_ws, "callerassign-agent")
        agent = await Agent.objects.aget(hash="callerassign-agent-hash")
        impl = await build_implementation_for_agent(agent.pk, "callerassign")

        # Originate work referencing our own implementation.
        await send_message(communicator, messages.CallerAssign(reference="r-1", implementation=str(impl.pk), args={"x": 1}))
        result = await _recv_kind(communicator, messages.ToAgentMessageType.CALLER_ASSIGN_RESULT.value)
        assert result["reference"] == "r-1" and result["created"] is True and result["assignation"]
        ass_id = result["assignation"]

        # Resend the SAME reference → same assignation, created=False, no duplicate row.
        await send_message(communicator, messages.CallerAssign(reference="r-1", implementation=str(impl.pk), args={"x": 1}))
        result2 = await _recv_kind(communicator, messages.ToAgentMessageType.CALLER_ASSIGN_RESULT.value)
        assert result2["assignation"] == ass_id and result2["created"] is False

        assert await Assignation.objects.filter(reference="r-1").acount() == 1

        # Origination is captured on the root assignation for the caller-death cascade:
        # the originating connection id is recorded (session id is None here — the test
        # Register sends no session_id).
        created = await Assignation.objects.aget(id=ass_id)
        assert created.originating_connection_id is not None
        await communicator.disconnect()

    async def test_caller_assign_dispatches_assign_command_to_executor(self, agent_ws):
        communicator, _ = await connect_and_register(agent_ws, "callerassign2-agent")
        agent = await Agent.objects.aget(hash="callerassign2-agent-hash")
        impl = await build_implementation_for_agent(agent.pk, "callerassign2")

        await send_message(communicator, messages.CallerAssign(reference="r-2", implementation=str(impl.pk), args={"y": 2}))

        # The agent is also the executor, so it receives the ASSIGN command for the work.
        assign = await _recv_kind(communicator, messages.ToAgentMessageType.ASSIGN.value)
        assert assign["interface"] == impl.interface and assign["args"] == {"y": 2}
        await communicator.disconnect()
