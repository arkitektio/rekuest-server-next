from kante.types import Info
import strawberry_django
import strawberry
from facade import types, models
from typing import AsyncGenerator
from facade.channels import agent_updated_listen


@strawberry.type
class AgentChangeEvent:
    event: types.AgentEvent | None
    create: types.Agent | None


async def agents(
    self,
    info: Info,
    instance_id: str,
) -> AsyncGenerator[types.AgentEvent, None]:
    """Join and subscribe to message sent to the given rooms."""

    registry, _ = await models.Registry.objects.aget_or_create(
        app=info.context.request.app, user=info.context.request.user
    )

    waiter, _ = await models.Waiter.objects.aget_or_create(
        registry=registry, instance_id=instance_id, defaults=dict(name="default")
    )

    async for message in agent_updated_listen(info, [f"agents"]):

        if message["type"] == "created":
            yield await models.Agent.objects.aget(id=message["id"])
        elif message["type"] == "updated":
            yield await models.Agent.objects.aget(id=message["id"])
