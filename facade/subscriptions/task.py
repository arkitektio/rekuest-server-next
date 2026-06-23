from kante.types import Info
import strawberry
from facade import types, models
from typing import AsyncGenerator
from facade.channels import task_event_channel, child_task_channel


async def task_events(
    self,
    info: Info,
) -> AsyncGenerator[types.TaskEvent, None]:
    """Join and subscribe to message sent to the given rooms."""

    caller, _ = await models.Caller.objects.aget_or_create(client=info.context.request.client, user=info.context.request.user, organization=info.context.request.organization)

    async for message in task_event_channel(info.context, [f"task_caller_{caller.id}"]):
        yield await models.TaskEvent.objects.aget(id=message)


@strawberry.type
class TaskChangeEvent:
    event: types.TaskEvent | None
    create: types.Task | None


async def tasks(
    self,
    info: Info,
) -> AsyncGenerator[TaskChangeEvent, None]:
    """Join and subscribe to message sent to the given rooms."""

    user = info.context.request.user
    client = info.context.request.client

    caller, _ = await models.Caller.objects.aget_or_create(client=client, user=user, organization=info.context.request.organization)

    async for message in task_event_channel.listen(info.context, [f"task_caller_{caller.id}"]):
        if message.create:
            task = await models.Task.objects.aget(id=message.create)
            yield TaskChangeEvent(create=task, event=None)
        elif message.event:
            event = await models.TaskEvent.objects.aget(id=message.event)
            yield TaskChangeEvent(event=event, create=None)


@strawberry.type
class ChildTaskEvent:
    create: types.Task | None
    update: types.Task | None


async def child_tasks(
    self,
    info: Info,
    id: strawberry.ID,
) -> AsyncGenerator[ChildTaskEvent, None]:
    """Join and subscribe to message sent to the given rooms."""

    user = info.context.request.user
    client = info.context.request.client

    task = await models.Task.objects.aget(id=id)

    async for message in child_task_channel.listen(info.context, [f"child_tasks_{task.id}"]):
        if message.create:
            task = await models.Task.objects.aget(id=message.create)
            yield ChildTaskEvent(create=task, update=None)
        elif message.update:
            update = await models.Task.objects.aget(id=message.update)
            yield ChildTaskEvent(update=update, create=None)
