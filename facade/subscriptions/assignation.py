from kante.types import Info
import strawberry
from facade import types, models
from typing import AsyncGenerator
from facade.channels import assignation_event_channel, child_assignation_channel


async def assignation_events(
    self,
    info: Info,
) -> AsyncGenerator[types.AssignationEvent, None]:
    """Join and subscribe to message sent to the given rooms."""

    registry, _ = await models.Registry.objects.aget_or_create(client=info.context.request.client, user=info.context.request.user, organization=info.context.request.organization)

    async for message in assignation_event_channel(info.context, [f"ass_registry_{registry.id}"]):
        yield await models.AssignationEvent.objects.aget(id=message)


@strawberry.type
class AssignationChangeEvent:
    event: types.AssignationEvent | None
    create: types.Assignation | None


async def assignations(
    self,
    info: Info,
) -> AsyncGenerator[AssignationChangeEvent, None]:
    """Join and subscribe to message sent to the given rooms."""

    user = info.context.request.user
    client = info.context.request.client

    registry, _ = await models.Registry.objects.aget_or_create(client=client, user=user, organization=info.context.request.organization)

    async for message in assignation_event_channel.listen(info.context, [f"ass_registry_{registry.id}"]):
        if message.create:
            ass = await models.Assignation.objects.aget(id=message.create)
            yield AssignationChangeEvent(create=ass, event=None)
        elif message.event:
            event = await models.AssignationEvent.objects.aget(id=message.event)
            yield AssignationChangeEvent(event=event, create=None)


@strawberry.type
class ChildAssignationEvent:
    create: types.Assignation | None
    update: types.Assignation | None


async def child_assignations(
    self,
    info: Info,
    id: strawberry.ID,
) -> AsyncGenerator[ChildAssignationEvent, None]:
    """Join and subscribe to message sent to the given rooms."""

    user = info.context.request.user
    client = info.context.request.client

    assignation = await models.Assignation.objects.aget(id=id)

    async for message in child_assignation_channel.listen(info.context, [f"child_assignations_{assignation.id}"]):
        if message.create:
            ass = await models.Assignation.objects.aget(id=message.create)
            yield ChildAssignationEvent(create=ass, update=None)
        elif message.update:
            update = await models.Assignation.objects.aget(id=message.update)
            yield ChildAssignationEvent(update=update, create=None)
