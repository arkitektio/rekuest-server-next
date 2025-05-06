from kante.types import Info
import strawberry
from facade import types, models
from typing import AsyncGenerator
from facade.channels import agent_updated_channel

@strawberry.type
class AgentChangeEvent:
    update: types.Agent | None = None
    create: types.Agent | None = None
    delete: strawberry.ID | None = None


async def agents(
    self,
    info: Info,
) -> AsyncGenerator[AgentChangeEvent, None]:
    """Join and subscribe to message sent to the given rooms."""
    
    user = info.context.request.user

    print("Agent subscription", [f"agents_for_{user.id}"])

    async for message in agent_updated_channel.listen(info.context, [f"agents_for_{user.id}"]):
        print("Message received", message)
        if message.create:
            yield AgentChangeEvent(create=await models.Agent.objects.aget(id=message.create))
        elif message.update:
            yield AgentChangeEvent(update=await models.Agent.objects.aget(id=message.update))
        elif message.delete:
            yield AgentChangeEvent(delete=message.delete)
        else:
            raise ValueError("Unknown message type")
