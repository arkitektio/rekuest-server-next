"""Full-stack task-event persistence over the agent socket.

Covers the Log/Progress/Yield/Done/Error/Critical/Cancelled events; state events
(StatePatch/StateSnapshot/SessionInit) live in ``test_state.py``.
"""

import pytest

from facade import enums, messages
from facade.models import Task, TaskEvent

from tests.agent.helpers import open_agent
from tests.factories import build_task


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
class TestAgentEvents:
    async def test_log_event_persists(self, agent_ws):
        task = await build_task("log")
        session = await open_agent(agent_ws, "log-agent")

        await session.send(messages.Log(task=str(task.pk), message="hello", level="INFO"))

        await session.disconnect()  # flush the event through before asserting
        events = [e async for e in TaskEvent.objects.filter(task_id=task.pk, kind=enums.TaskEventKind.LOG)]
        assert len(events) == 1
        assert events[0].message == "hello"

    async def test_progress_event_persists(self, agent_ws):
        task = await build_task("progress")
        session = await open_agent(agent_ws, "progress-agent")

        await session.send(messages.Progress(task=str(task.pk), progress=42, message="halfway"))

        await session.disconnect()
        event = await TaskEvent.objects.filter(task_id=task.pk, kind=enums.TaskEventKind.PROGRESS).aget()
        assert event.progress == 42
        assert event.message == "halfway"

    async def test_yield_event_persists(self, agent_ws):
        task = await build_task("yield")
        session = await open_agent(agent_ws, "yield-agent")

        await session.send(messages.Yield(task=str(task.pk), returns={"out": 1}))

        await session.disconnect()
        event = await TaskEvent.objects.filter(task_id=task.pk, kind=enums.TaskEventKind.YIELD).aget()
        assert event.returns == {"out": 1}

    async def test_done_event_marks_task_done(self, agent_ws):
        task = await build_task("done")
        session = await open_agent(agent_ws, "done-agent")

        await session.send(messages.Completed(task=str(task.pk)))

        await session.disconnect()
        assert await TaskEvent.objects.filter(task_id=task.pk, kind=enums.TaskEventKind.COMPLETED).aexists()
        refreshed = await Task.objects.aget(pk=task.pk)
        assert refreshed.is_done is True
        assert refreshed.latest_event_kind == enums.TaskEventKind.COMPLETED
        assert refreshed.finished_at is not None

    async def test_error_event_marks_task_done(self, agent_ws):
        task = await build_task("error")
        session = await open_agent(agent_ws, "error-agent")

        await session.send(messages.Failed(task=str(task.pk), error="boom"))

        await session.disconnect()
        event = await TaskEvent.objects.filter(task_id=task.pk, kind=enums.TaskEventKind.FAILED).aget()
        assert event.message == "boom"
        refreshed = await Task.objects.aget(pk=task.pk)
        assert refreshed.is_done is True
        assert refreshed.latest_event_kind == enums.TaskEventKind.FAILED

    async def test_critical_event_marks_task_done(self, agent_ws):
        task = await build_task("critical")
        session = await open_agent(agent_ws, "critical-agent")

        await session.send(messages.Critical(task=str(task.pk), error="fatal"))

        await session.disconnect()
        event = await TaskEvent.objects.filter(task_id=task.pk, kind=enums.TaskEventKind.CRITICAL).aget()
        assert event.message == "fatal"
        refreshed = await Task.objects.aget(pk=task.pk)
        assert refreshed.latest_event_kind == enums.TaskEventKind.CRITICAL

    async def test_cancelled_event_marks_task_done(self, agent_ws):
        task = await build_task("cancelled")
        session = await open_agent(agent_ws, "cancelled-agent")

        await session.send(messages.Cancelled(task=str(task.pk)))

        await session.disconnect()
        assert await TaskEvent.objects.filter(task_id=task.pk, kind=enums.TaskEventKind.CANCELLED).aexists()
        refreshed = await Task.objects.aget(pk=task.pk)
        assert refreshed.is_done is True
        assert refreshed.latest_event_kind == enums.TaskEventKind.CANCELLED
