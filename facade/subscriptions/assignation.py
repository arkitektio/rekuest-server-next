from kante.types import Info
import strawberry
from facade import types, models, scalars
from typing import AsyncGenerator
from facade.channels import assignation_event_channel


async def assignation_events(
    self,
    info: Info,
    instance_id: scalars.InstanceID,
) -> AsyncGenerator[types.AssignationEvent, None]:
    """Join and subscribe to message sent to the given rooms."""



    registry, _ = await models.Registry.objects.aget_or_create(client=info.context.request.client, user=info.context.request.user)

    waiter, _ = await models.Waiter.objects.aget_or_create(
        registry=registry, instance_id=instance_id, defaults=dict(name="default")
    )

    async for message in assignation_event_channel(
        info.context, [f"waiter_{waiter.id}"]
    ):
        yield await models.AssignationEvent.objects.aget(id=message)


@strawberry.type
class AssignationChangeEvent:
    event: types.AssignationEvent | None
    create: types.Assignation | None


async def assignations(
    self,
    info: Info,
    instance_id: scalars.InstanceID,
) -> AsyncGenerator[AssignationChangeEvent, None]:
    """Join and subscribe to message sent to the given rooms."""

    user = info.context.request.user
    client = info.context.request.client

    registry, _ = await models.Registry.objects.aget_or_create(client=client, user=user)

    waiter, _ = await models.Waiter.objects.aget_or_create(
        registry=registry, instance_id=instance_id, defaults=dict(name="default")
    )

    async for message in assignation_event_channel.listen(
        info.context, [f"ass_waiter_{waiter.id}"]
    ):
        if message.create:
            ass = await models.Assignation.objects.aget(id=message.create)
            yield AssignationChangeEvent(create=ass, event=None)
        elif message.event:
            event = await models.AssignationEvent.objects.aget(id=message.event)
            yield AssignationChangeEvent(event=event, create=None)
