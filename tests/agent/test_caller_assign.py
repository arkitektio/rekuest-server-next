"""Full-stack caller-assign over the agent socket (item 4).

A participant originates work via ``CallerAssign`` and gets a ``CallerAssignResult`` back.
Here the registered agent assigns to its own implementation, so it both originates the work
(caller) and receives the ``ASSIGN`` command (executor). Idempotency: resending the same
``reference`` returns the same assignation with ``created=False``.
"""

import pytest

from facade import messages
from facade.models import Assignation

from tests.agent.helpers import open_agent
from tests.factories import build_implementation_for_agent


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
class TestCallerAssign:
    async def test_caller_assign_creates_then_is_idempotent(self, agent_ws):
        session = await open_agent(agent_ws, "callerassign-agent")
        impl = await build_implementation_for_agent(session.agent.pk, "callerassign")

        # Originate work referencing our own implementation.
        await session.send(messages.CallerAssign(reference="r-1", implementation=str(impl.pk), args={"x": 1}))
        result = await session.receive(messages.CallerAssignResult)
        assert result.reference == "r-1" and result.created is True and result.assignation

        # Resend the SAME reference → same assignation, created=False, no duplicate row.
        await session.send(messages.CallerAssign(reference="r-1", implementation=str(impl.pk), args={"x": 1}))
        result2 = await session.receive(messages.CallerAssignResult)
        assert result2.assignation == result.assignation and result2.created is False

        assert await Assignation.objects.filter(reference="r-1").acount() == 1

        # Origination is captured on the root assignation for the caller-death cascade:
        # the originating connection id is recorded (session id is None here — the test
        # Register sends no session_id).
        created = await Assignation.objects.aget(id=result.assignation)
        assert created.originating_connection_id is not None
        await session.disconnect()

    async def test_caller_assign_dispatches_assign_command_to_executor(self, agent_ws):
        session = await open_agent(agent_ws, "callerassign2-agent")
        impl = await build_implementation_for_agent(session.agent.pk, "callerassign2")

        await session.send(messages.CallerAssign(reference="r-2", implementation=str(impl.pk), args={"y": 2}))

        # The agent is also the executor, so it receives the ASSIGN command for the work.
        assign = await session.receive(messages.Assign)
        assert assign.interface == impl.interface and assign.args == {"y": 2}
        await session.disconnect()
