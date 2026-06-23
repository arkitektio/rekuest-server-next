"""Full-stack caller-event return path (item 8).

When an agent is the *caller* of a task, events on that task are streamed
back to its own socket as ``Caller*`` messages. Here the registered agent is both the
executor (it reports a ProgressEvent) and the caller (the task's caller is its own
identity), so the progress it reports comes straight back to it as a ``ProgressEvent``.
"""

import pytest

from facade import messages

from tests.agent.helpers import open_agent
from tests.factories import build_task, build_task_for_agent_caller


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
class TestCallerEventReturn:
    async def test_caller_receives_progress_for_own_task(self, agent_ws):
        session = await open_agent(agent_ws, "callerev-agent")
        task = await build_task_for_agent_caller(session.agent.pk, "callerev")

        # Report progress as the executor …
        await session.send(messages.Progress(task=str(task.pk), progress=42, message="halfway"))

        # … and receive it back as the caller.
        msg = await session.receive(messages.ProgressEvent)
        assert msg.task == str(task.pk)
        assert msg.progress == 42 and msg.message == "halfway"
        assert msg.event and msg.seq  # dedup handle + ordering key present

        await session.disconnect()

    async def test_done_comes_back_as_caller_done(self, agent_ws):
        session = await open_agent(agent_ws, "callerdone-agent")
        task = await build_task_for_agent_caller(session.agent.pk, "callerdone")

        await session.send(messages.Completed(task=str(task.pk)))

        msg = await session.receive(messages.CompletedEvent)
        assert msg.task == str(task.pk)
        await session.disconnect()

    async def test_only_own_caller_tasks_are_delivered(self, agent_ws):
        # Two tasks: one whose caller is us, one whose caller is a different identity.
        # Progress is reported on the OTHER first, then on OURS. Only ours must come back,
        # so the single ProgressEvent we receive must be for our task (progress 77),
        # never the other's (progress 10).
        session = await open_agent(agent_ws, "calleriso-agent")
        mine = await build_task_for_agent_caller(session.agent.pk, "callermine")
        other = await build_task("callerother")  # caller = its own identity, not ours

        await session.send(messages.Progress(task=str(other.pk), progress=10))
        await session.send(messages.Progress(task=str(mine.pk), progress=77))

        msg = await session.receive(messages.ProgressEvent)
        assert msg.task == str(mine.pk) and msg.progress == 77

        await session.disconnect()
