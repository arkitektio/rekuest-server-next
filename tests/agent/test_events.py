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
        session = await open_agent(agent_ws, "log-agent")
        task = await build_task("log", agent_pk=session.agent_pk)

        await session.send(messages.Log(task=str(task.pk), message="hello", level="ERROR"))

        await session.disconnect()  # flush the event through before asserting
        events = [e async for e in TaskEvent.objects.filter(task_id=task.pk, kind=enums.TaskEventKind.LOG)]
        assert len(events) == 1
        assert events[0].message == "hello"
        assert str(events[0].level) == "ERROR"  # the agent-sent level is persisted, not dropped

    async def test_progress_event_persists(self, agent_ws):
        session = await open_agent(agent_ws, "progress-agent")
        task = await build_task("progress", agent_pk=session.agent_pk)

        await session.send(messages.Progress(task=str(task.pk), progress=42, message="halfway"))

        await session.disconnect()
        event = await TaskEvent.objects.filter(task_id=task.pk, kind=enums.TaskEventKind.PROGRESS).aget()
        assert event.progress == 42
        assert event.message == "halfway"

    async def test_yield_event_persists(self, agent_ws):
        session = await open_agent(agent_ws, "yield-agent")
        task = await build_task("yield", agent_pk=session.agent_pk)

        await session.send(messages.Yield(task=str(task.pk), returns={"out": 1}))

        await session.disconnect()
        event = await TaskEvent.objects.filter(task_id=task.pk, kind=enums.TaskEventKind.YIELD).aget()
        assert event.returns == {"out": 1}

    async def test_done_event_marks_task_done(self, agent_ws):
        session = await open_agent(agent_ws, "done-agent")
        task = await build_task("done", agent_pk=session.agent_pk)

        await session.send(messages.Completed(task=str(task.pk)))

        await session.disconnect()
        assert await TaskEvent.objects.filter(task_id=task.pk, kind=enums.TaskEventKind.COMPLETED).aexists()
        refreshed = await Task.objects.aget(pk=task.pk)
        assert refreshed.is_done is True
        assert refreshed.latest_event_kind == enums.TaskEventKind.COMPLETED
        assert refreshed.finished_at is not None

    async def test_error_event_marks_task_done(self, agent_ws):
        session = await open_agent(agent_ws, "error-agent")
        task = await build_task("error", agent_pk=session.agent_pk)

        await session.send(messages.Failed(task=str(task.pk), error="boom"))

        await session.disconnect()
        event = await TaskEvent.objects.filter(task_id=task.pk, kind=enums.TaskEventKind.FAILED).aget()
        assert event.message == "boom"
        refreshed = await Task.objects.aget(pk=task.pk)
        assert refreshed.is_done is True
        assert refreshed.latest_event_kind == enums.TaskEventKind.FAILED

    async def test_critical_event_marks_task_done(self, agent_ws):
        session = await open_agent(agent_ws, "critical-agent")
        task = await build_task("critical", agent_pk=session.agent_pk)

        await session.send(messages.Critical(task=str(task.pk), error="fatal"))

        await session.disconnect()
        event = await TaskEvent.objects.filter(task_id=task.pk, kind=enums.TaskEventKind.CRITICAL).aget()
        assert event.message == "fatal"
        refreshed = await Task.objects.aget(pk=task.pk)
        assert refreshed.latest_event_kind == enums.TaskEventKind.CRITICAL

    async def test_cancelled_event_marks_task_done(self, agent_ws):
        session = await open_agent(agent_ws, "cancelled-agent")
        task = await build_task("cancelled", agent_pk=session.agent_pk)

        await session.send(messages.Cancelled(task=str(task.pk)))

        await session.disconnect()
        assert await TaskEvent.objects.filter(task_id=task.pk, kind=enums.TaskEventKind.CANCELLED).aexists()
        refreshed = await Task.objects.aget(pk=task.pk)
        assert refreshed.is_done is True
        assert refreshed.latest_event_kind == enums.TaskEventKind.CANCELLED

    async def test_agent_cannot_report_on_another_agents_task(self, agent_ws):
        """An agent may only report on its own work.

        The socket is authenticated but the task id inside the frame is not, so without an
        ``agent_id`` predicate any agent could terminate — or inject results into — any task in
        any organization just by naming its id. The task here belongs to a *different* agent.
        """
        victim_task = await build_task("victim")  # owned by its own throwaway agent
        session = await open_agent(agent_ws, "attacker-agent")

        await session.send(messages.Completed(task=str(victim_task.pk)))
        await session.disconnect()

        refreshed = await Task.objects.aget(pk=victim_task.pk)
        assert refreshed.is_done is False, "an unrelated agent completed someone else's task"
        assert not await TaskEvent.objects.filter(task_id=victim_task.pk, kind=enums.TaskEventKind.COMPLETED).aexists()

    async def test_agent_cannot_inject_yield_into_another_agents_task(self, agent_ws):
        """The result-forgery variant: a Yield carries a payload the caller receives as genuine."""
        victim_task = await build_task("victim-yield")
        session = await open_agent(agent_ws, "attacker-yield-agent")

        await session.send(messages.Yield(task=str(victim_task.pk), returns={"owned": True}))
        await session.disconnect()

        assert not await TaskEvent.objects.filter(task_id=victim_task.pk, kind=enums.TaskEventKind.YIELD).aexists()
