import datetime

from kante.types import Info
import strawberry
from facade import models, enums, types
from rekuest_core import scalars as rscalars
from typing import AsyncGenerator
from facade.channels import task_event_channel, child_task_channel, agent_task_channel


@strawberry.type(description="Slim, non-traversable snapshot of a task for change feeds.")
class TaskChange:
    id: strawberry.ID
    reference: str | None
    is_done: bool
    latest_event_kind: enums.TaskEventKind
    latest_instruct_kind: enums.TaskInstructKind
    status_message: str | None
    action: strawberry.ID
    implementation: strawberry.ID | None
    agent: strawberry.ID | None
    root: strawberry.ID | None
    parent: strawberry.ID | None
    created_at: datetime.datetime
    updated_at: datetime.datetime
    finished_at: datetime.datetime | None

    @classmethod
    def from_model(cls, t: models.Task) -> "TaskChange":
        return cls(
            id=strawberry.ID(str(t.id)),
            reference=t.reference,
            is_done=t.is_done,
            latest_event_kind=enums.TaskEventKind(t.latest_event_kind),
            latest_instruct_kind=enums.TaskInstructKind(t.latest_instruct_kind),
            status_message=t.statusmessage or None,
            action=strawberry.ID(str(t.action_id)),
            implementation=strawberry.ID(str(t.implementation_id)) if t.implementation_id else None,
            agent=strawberry.ID(str(t.agent_id)) if t.agent_id else None,
            root=strawberry.ID(str(t.root_id)) if t.root_id else None,
            parent=strawberry.ID(str(t.parent_id)) if t.parent_id else None,
            created_at=t.created_at,
            updated_at=t.updated_at,
            finished_at=t.finished_at,
        )


@strawberry.type(description="Slim, non-traversable task event for change feeds.")
class TaskEventChange:
    id: strawberry.ID
    task: strawberry.ID
    kind: enums.TaskEventKind
    message: str | None
    progress: int | None
    returns: rscalars.AnyDefault | None
    created_at: datetime.datetime

    @classmethod
    def from_model(cls, e: models.TaskEvent) -> "TaskEventChange":
        return cls(
            id=strawberry.ID(str(e.id)),
            task=strawberry.ID(str(e.task_id)),
            kind=enums.TaskEventKind(e.kind),
            message=e.message,
            progress=e.progress,
            returns=e.returns,
            created_at=e.created_at,
        )


@strawberry.type
class TaskChangeEvent:
    event: TaskEventChange | None
    create: TaskChange | None


@strawberry.type
class ChildTaskEvent:
    create: TaskChange | None
    update: TaskChange | None


async def _build_change(message) -> TaskChangeEvent:
    """Build a slim TaskChangeEvent from a channel message (create or event id)."""
    if message.create:
        task = await models.Task.objects.aget(id=message.create)
        return TaskChangeEvent(create=TaskChange.from_model(task), event=None)

    event = await models.TaskEvent.objects.aget(id=message.event)
    return TaskChangeEvent(event=TaskEventChange.from_model(event), create=None)


async def mytasks(
    self,
    info: Info,
) -> AsyncGenerator[TaskChangeEvent, None]:
    """Subscribe to root tasks (and their events) created by this client (caller-scoped)."""

    caller, _ = await models.Caller.objects.aget_or_create(
        client=info.context.request.client,
        user=info.context.request.user,
        organization=info.context.request.organization,
    )

    async for message in task_event_channel.listen(info.context, [f"root_tasks_caller_{caller.id}"]):
        yield await _build_change(message)


async def tasks(
    self,
    info: Info,
) -> AsyncGenerator[TaskChangeEvent, None]:
    """Subscribe to root task changes (and their events) across the whole organization."""

    organization = info.context.request.organization

    async for message in task_event_channel.listen(info.context, [f"root_tasks_org_{organization.id}"]):
        yield await _build_change(message)


@strawberry.type
class AgentTaskUpdate:
    create: types.Task | None
    update: types.Task | None


async def agent_tasks(
    self,
    info: Info,
    agent: strawberry.ID,
) -> AsyncGenerator[AgentTaskUpdate, None]:
    """Subscribe to task create/update for a single agent (its detail-page "latest tasks" feed)."""

    async for message in agent_task_channel.listen(info.context, [f"agent_tasks_{agent}"]):
        if message.create:
            task = await models.Task.objects.aget(id=message.create)
            yield AgentTaskUpdate(create=task, update=None)
        elif message.update:
            task = await models.Task.objects.aget(id=message.update)
            yield AgentTaskUpdate(create=None, update=task)


async def child_tasks(
    self,
    info: Info,
    id: strawberry.ID,
) -> AsyncGenerator[ChildTaskEvent, None]:
    """Subscribe to all descendant task changes of a given task (any task whose root or parent is it)."""

    task = await models.Task.objects.aget(id=id)

    async for message in child_task_channel.listen(info.context, [f"child_tasks_{task.id}"]):
        if message.create:
            child = await models.Task.objects.aget(id=message.create)
            yield ChildTaskEvent(create=TaskChange.from_model(child), update=None)
        elif message.update:
            child = await models.Task.objects.aget(id=message.update)
            yield ChildTaskEvent(update=TaskChange.from_model(child), create=None)
