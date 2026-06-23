"""Full-stack assignation-event persistence over the agent socket.

Covers the Log/Progress/Yield/Done/Error/Critical/Cancelled events; state events
(StatePatch/StateSnapshot/SessionInit) live in ``test_state.py``.
"""

import pytest

from facade import enums, messages
from facade.models import Assignation, AssignationEvent

from tests.agent.helpers import open_agent
from tests.factories import build_assignation


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
class TestAgentEvents:
    async def test_log_event_persists(self, agent_ws):
        assignation = await build_assignation("log")
        session = await open_agent(agent_ws, "log-agent")

        await session.send(messages.Log(assignation=str(assignation.pk), message="hello", level="INFO"))

        await session.disconnect()  # flush the event through before asserting
        events = [e async for e in AssignationEvent.objects.filter(assignation_id=assignation.pk, kind=enums.AssignationEventKind.LOG)]
        assert len(events) == 1
        assert events[0].message == "hello"

    async def test_progress_event_persists(self, agent_ws):
        assignation = await build_assignation("progress")
        session = await open_agent(agent_ws, "progress-agent")

        await session.send(messages.Progress(assignation=str(assignation.pk), progress=42, message="halfway"))

        await session.disconnect()
        event = await AssignationEvent.objects.filter(assignation_id=assignation.pk, kind=enums.AssignationEventKind.PROGRESS).aget()
        assert event.progress == 42
        assert event.message == "halfway"

    async def test_yield_event_persists(self, agent_ws):
        assignation = await build_assignation("yield")
        session = await open_agent(agent_ws, "yield-agent")

        await session.send(messages.Yield(assignation=str(assignation.pk), returns={"out": 1}))

        await session.disconnect()
        event = await AssignationEvent.objects.filter(assignation_id=assignation.pk, kind=enums.AssignationEventKind.YIELD).aget()
        assert event.returns == {"out": 1}

    async def test_done_event_marks_assignation_done(self, agent_ws):
        assignation = await build_assignation("done")
        session = await open_agent(agent_ws, "done-agent")

        await session.send(messages.Completed(assignation=str(assignation.pk)))

        await session.disconnect()
        assert await AssignationEvent.objects.filter(assignation_id=assignation.pk, kind=enums.AssignationEventKind.COMPLETED).aexists()
        refreshed = await Assignation.objects.aget(pk=assignation.pk)
        assert refreshed.is_done is True
        assert refreshed.latest_event_kind == enums.AssignationEventKind.COMPLETED
        assert refreshed.finished_at is not None

    async def test_error_event_marks_assignation_done(self, agent_ws):
        assignation = await build_assignation("error")
        session = await open_agent(agent_ws, "error-agent")

        await session.send(messages.Failed(assignation=str(assignation.pk), error="boom"))

        await session.disconnect()
        event = await AssignationEvent.objects.filter(assignation_id=assignation.pk, kind=enums.AssignationEventKind.FAILED).aget()
        assert event.message == "boom"
        refreshed = await Assignation.objects.aget(pk=assignation.pk)
        assert refreshed.is_done is True
        assert refreshed.latest_event_kind == enums.AssignationEventKind.FAILED

    async def test_critical_event_marks_assignation_done(self, agent_ws):
        assignation = await build_assignation("critical")
        session = await open_agent(agent_ws, "critical-agent")

        await session.send(messages.Critical(assignation=str(assignation.pk), error="fatal"))

        await session.disconnect()
        event = await AssignationEvent.objects.filter(assignation_id=assignation.pk, kind=enums.AssignationEventKind.CRITICAL).aget()
        assert event.message == "fatal"
        refreshed = await Assignation.objects.aget(pk=assignation.pk)
        assert refreshed.latest_event_kind == enums.AssignationEventKind.CRITICAL

    async def test_cancelled_event_marks_assignation_done(self, agent_ws):
        assignation = await build_assignation("cancelled")
        session = await open_agent(agent_ws, "cancelled-agent")

        await session.send(messages.Cancelled(assignation=str(assignation.pk)))

        await session.disconnect()
        assert await AssignationEvent.objects.filter(assignation_id=assignation.pk, kind=enums.AssignationEventKind.CANCELLED).aexists()
        refreshed = await Assignation.objects.aget(pk=assignation.pk)
        assert refreshed.is_done is True
        assert refreshed.latest_event_kind == enums.AssignationEventKind.CANCELLED
