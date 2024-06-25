from kante.types import Info
import strawberry_django
import strawberry
from facade import types, models, scalars
from typing import AsyncGenerator
from facade.channels import node_created_listen, assignation_event_listen, assignation_listen


async def assignation_events(
    self,
    info: Info,
    instance_id: scalars.InstanceID,
) -> AsyncGenerator[types.AssignationEvent, None]:
    """Join and subscribe to message sent to the given rooms."""

    print(info)

    registry, _ = await models.Registry.objects.aget_or_create(
        app=info.context.request.app, user=info.context.request.user
    )

    waiter, _ = await models.Waiter.objects.aget_or_create(
        registry=registry, instance_id=instance_id, defaults=dict(name="default")
    )

    async for message in assignation_event_listen(info, [f"waiter_{waiter.id}"]):
        print("ID: ", message)
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

    registry, _ = await models.Registry.objects.aget_or_create(
        app=info.context.request.app, user=info.context.request.user
    )

    waiter, _ = await models.Waiter.objects.aget_or_create(
        registry=registry, instance_id=instance_id, defaults=dict(name="default")
    )

    async for message in assignation_listen(info, [f"ass_waiter_{waiter.id}"]):
        print("ID", message)


        if message["type"] == "created":
            ass = await models.Assignation.objects.aget(id=message["id"])
            yield AssignationChangeEvent(create=ass, event=None)
        else:
            event = await models.AssignationEvent.objects.aget(id=message["id"])
            yield AssignationChangeEvent(event=event, create=None)
