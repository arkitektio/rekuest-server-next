"""Two-phase lifecycle controls over the socket: a caller drives cancel/interrupt/pause/
resume on a *different* executor agent, and observes the outcome as Caller* mirrors.

Each op is two-phase: the caller's request is acked (`ControlResponse`), the executor
receives the ToAgent control message and an `-ING` mirror reaches the caller; the resolved
state arrives only when the executor sends the confirmation event (→ the `-ED` mirror).
"""

import pytest

from facade import enums, messages
from facade.models import Task

from tests.agent.helpers import open_agent
from tests.factories import build_task, build_implementation_for_agent

EXECUTOR_TOKEN = "test2"


async def _assigned_pair(agent_ws, prefix):
    """A connected (caller, executor) pair with one task the caller owns; returns its id."""
    executor = await open_agent(agent_ws, f"{prefix}-exec", token=EXECUTOR_TOKEN)
    impl = await build_implementation_for_agent(executor.agent_pk, prefix)
    caller = await open_agent(agent_ws, f"{prefix}-caller")
    await caller.send(messages.AssignRequest(reference=f"{prefix}-r", implementation=str(impl.pk), args={}))
    await caller.receive(messages.AssignResponse)
    assign = await executor.receive(messages.Assign)
    return caller, executor, assign.task


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
class TestLifecycleRoundTrips:
    async def test_cancel_round_trip(self, agent_ws):
        caller, executor, ass_id = await _assigned_pair(agent_ws, "lc-cancel")

        await caller.send(messages.CancelRequest(task=ass_id))
        assert (await caller.receive(messages.ControlResponse)).accepted is True
        assert (await executor.receive(messages.Cancel)).task == ass_id  # request, not terminal
        assert (await caller.receive(messages.CancellingEvent)).task == ass_id

        await executor.send(messages.Cancelled(task=ass_id))  # confirm → terminal
        assert (await caller.receive(messages.CancelledEvent)).task == ass_id
        refreshed = await Task.objects.aget(pk=ass_id)
        assert refreshed.is_done is True and refreshed.latest_event_kind == enums.TaskEventKind.CANCELLED
        await caller.disconnect()
        await executor.disconnect()

    async def test_interrupt_round_trip(self, agent_ws):
        caller, executor, ass_id = await _assigned_pair(agent_ws, "lc-int")

        await caller.send(messages.InterruptRequest(task=ass_id))
        assert (await caller.receive(messages.ControlResponse)).accepted is True
        assert (await executor.receive(messages.Interrupt)).task == ass_id
        assert (await caller.receive(messages.InterruptingEvent)).task == ass_id

        await executor.send(messages.Interrupted(task=ass_id))
        assert (await caller.receive(messages.InterruptedEvent)).task == ass_id
        refreshed = await Task.objects.aget(pk=ass_id)
        assert refreshed.is_done is True and refreshed.latest_event_kind == enums.TaskEventKind.INTERRUPTED
        await caller.disconnect()
        await executor.disconnect()

    async def test_pause_round_trip_is_non_terminal(self, agent_ws):
        caller, executor, ass_id = await _assigned_pair(agent_ws, "lc-pause")

        await caller.send(messages.PauseRequest(task=ass_id))
        assert (await caller.receive(messages.ControlResponse)).accepted is True
        assert (await executor.receive(messages.Pause)).task == ass_id
        assert (await caller.receive(messages.PausingEvent)).task == ass_id

        await executor.send(messages.Paused(task=ass_id))
        assert (await caller.receive(messages.PausedEvent)).task == ass_id
        refreshed = await Task.objects.aget(pk=ass_id)
        assert refreshed.is_done is False and refreshed.latest_event_kind == enums.TaskEventKind.PAUSED
        await caller.disconnect()
        await executor.disconnect()

    async def test_resume_with_step_forwards_the_step_flag(self, agent_ws):
        # Stepping is now resume(step=True) — the executor receives a Resume carrying step=True
        # (and the old standalone Step message is gone).
        caller, executor, ass_id = await _assigned_pair(agent_ws, "lc-step")

        await caller.send(messages.ResumeRequest(task=ass_id, step=True))
        assert (await caller.receive(messages.ControlResponse)).accepted is True
        resume = await executor.receive(messages.Resume)
        assert resume.task == ass_id and resume.step is True
        assert (await caller.receive(messages.ResumingEvent)).task == ass_id

        await executor.send(messages.Resumed(task=ass_id))
        assert (await caller.receive(messages.ResumedEvent)).task == ass_id
        await caller.disconnect()
        await executor.disconnect()

    async def test_pause_resume_done_sequence(self, agent_ws):
        caller, executor, ass_id = await _assigned_pair(agent_ws, "lc-prd")

        await caller.send(messages.PauseRequest(task=ass_id))
        await caller.receive(messages.ControlResponse)
        await executor.receive(messages.Pause)
        await executor.send(messages.Paused(task=ass_id))
        assert (await caller.receive(messages.PausedEvent)).task == ass_id

        await caller.send(messages.ResumeRequest(task=ass_id))
        await caller.receive(messages.ControlResponse)
        await executor.receive(messages.Resume)  # NOT Cancel (regression)
        await executor.send(messages.Resumed(task=ass_id))
        assert (await caller.receive(messages.ResumedEvent)).task == ass_id

        await executor.send(messages.Completed(task=ass_id))
        assert (await caller.receive(messages.CompletedEvent)).task == ass_id
        refreshed = await Task.objects.aget(pk=ass_id)
        assert refreshed.is_done is True and refreshed.latest_event_kind == enums.TaskEventKind.COMPLETED
        await caller.disconnect()
        await executor.disconnect()


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
class TestLifecycleFailures:
    async def test_cancel_non_owned_task_nacks_without_closing(self, agent_ws):
        caller = await open_agent(agent_ws, "lc-noown-caller")
        foreign = await build_task("lc-noown")  # caller = a different identity

        await caller.send(messages.CancelRequest(task=str(foreign.pk)))
        result = await caller.receive(messages.ControlResponse)
        assert result.accepted is False and result.error
        # socket stays open: a second op still gets a (nack) reply.
        await caller.send(messages.CancelRequest(task="999999999"))
        assert (await caller.receive(messages.ControlResponse)).accepted is False
        await caller.disconnect()

    async def test_confirmation_event_no_longer_closes_socket(self, agent_ws):
        # Regression: Interrupted/Paused/Resumed used to hit the router's `case _` and close the
        # socket. Now they're handled and acked; an unknown task is swallowed.
        session = await open_agent(agent_ws, "lc-confirm")
        task = await build_task("lc-confirm-ass")

        await session.send(messages.Paused(task=str(task.pk)))
        ack = await session.receive(messages.EventAck)
        assert ack.task == str(task.pk)

        # even for an unknown task: swallowed, still acked, socket open.
        await session.send(messages.Resumed(task="999999999"))
        assert await session.receive(messages.EventAck)
        await session.disconnect()
