"""Full-stack assignation-event persistence over the agent socket.

Covers the Log/Progress/Yield/Done/Error/Critical/Cancelled events; state events
(StatePatch/StateSnapshot/SessionInit) live in ``test_state.py``.
"""

import pytest

from facade import enums, messages
from facade.models import Assignation, AssignationEvent

from tests.agent.helpers import connect_and_register, send_message
from tests.factories import build_assignation


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
class TestAgentEvents:
    async def test_log_event_persists(self, agent_ws):
        assignation = await build_assignation("log")
        communicator, _ = await connect_and_register(agent_ws, "log-agent")

        await send_message(communicator, messages.LogEvent(assignation=str(assignation.pk), message="hello", level="INFO"))

        await communicator.disconnect()  # flush the event through before asserting
        events = [e async for e in AssignationEvent.objects.filter(assignation_id=assignation.pk, kind=enums.AssignationEventKind.LOG)]
        assert len(events) == 1
        assert events[0].message == "hello"

    async def test_progress_event_persists(self, agent_ws):
        assignation = await build_assignation("progress")
        communicator, _ = await connect_and_register(agent_ws, "progress-agent")

        await send_message(communicator, messages.ProgressEvent(assignation=str(assignation.pk), progress=42, message="halfway"))

        await communicator.disconnect()
        event = await AssignationEvent.objects.filter(assignation_id=assignation.pk, kind=enums.AssignationEventKind.PROGRESS).aget()
        assert event.progress == 42
        assert event.message == "halfway"

    async def test_yield_event_persists(self, agent_ws):
        assignation = await build_assignation("yield")
        communicator, _ = await connect_and_register(agent_ws, "yield-agent")

        await send_message(communicator, messages.YieldEvent(assignation=str(assignation.pk), returns={"out": 1}))

        await communicator.disconnect()
        event = await AssignationEvent.objects.filter(assignation_id=assignation.pk, kind=enums.AssignationEventKind.YIELD).aget()
        assert event.returns == {"out": 1}

    async def test_done_event_marks_assignation_done(self, agent_ws):
        assignation = await build_assignation("done")
        communicator, _ = await connect_and_register(agent_ws, "done-agent")

        await send_message(communicator, messages.DoneEvent(assignation=str(assignation.pk)))

        await communicator.disconnect()
        assert await AssignationEvent.objects.filter(assignation_id=assignation.pk, kind=enums.AssignationEventKind.DONE).aexists()
        refreshed = await Assignation.objects.aget(pk=assignation.pk)
        assert refreshed.is_done is True
        assert refreshed.latest_event_kind == enums.AssignationEventKind.DONE
        assert refreshed.finished_at is not None

    async def test_error_event_marks_assignation_done(self, agent_ws):
        assignation = await build_assignation("error")
        communicator, _ = await connect_and_register(agent_ws, "error-agent")

        await send_message(communicator, messages.ErrorEvent(assignation=str(assignation.pk), error="boom"))

        await communicator.disconnect()
        event = await AssignationEvent.objects.filter(assignation_id=assignation.pk, kind=enums.AssignationEventKind.ERROR).aget()
        assert event.message == "boom"
        refreshed = await Assignation.objects.aget(pk=assignation.pk)
        assert refreshed.is_done is True
        assert refreshed.latest_event_kind == enums.AssignationEventKind.ERROR

    async def test_critical_event_marks_assignation_done(self, agent_ws):
        assignation = await build_assignation("critical")
        communicator, _ = await connect_and_register(agent_ws, "critical-agent")

        await send_message(communicator, messages.CriticalEvent(assignation=str(assignation.pk), error="fatal"))

        await communicator.disconnect()
        event = await AssignationEvent.objects.filter(assignation_id=assignation.pk, kind=enums.AssignationEventKind.CRITICAL).aget()
        assert event.message == "fatal"
        refreshed = await Assignation.objects.aget(pk=assignation.pk)
        assert refreshed.latest_event_kind == enums.AssignationEventKind.CRITICAL

    async def test_cancelled_event_marks_assignation_done(self, agent_ws):
        assignation = await build_assignation("cancelled")
        communicator, _ = await connect_and_register(agent_ws, "cancelled-agent")

        await send_message(communicator, messages.CancelledEvent(assignation=str(assignation.pk)))

        await communicator.disconnect()
        assert await AssignationEvent.objects.filter(assignation_id=assignation.pk, kind=enums.AssignationEventKind.CANCELLED).aexists()
        refreshed = await Assignation.objects.aget(pk=assignation.pk)
        assert refreshed.is_done is True
        assert refreshed.latest_event_kind == enums.AssignationEventKind.CANCELLED
