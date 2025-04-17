from kante.types import Info
import strawberry_django
import strawberry
from facade import types, models
from typing import AsyncGenerator
from facade.channels import agent_updated_listen


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
    
    print("Agent subscription", [f"agents_for_{info.context.request.user.id}"])

    async for message in agent_updated_listen(info, [f"agents_for_{info.context.request.user.id}"]):
        print("Message received", message)
        if message["type"] == "create":
            yield AgentChangeEvent(create=await models.Agent.objects.aget(id=message["id"]))
        elif message["type"] == "update":
            yield AgentChangeEvent(update=await models.Agent.objects.aget(id=message["id"]))
        elif message["type"] == "delete":
            yield AgentChangeEvent(delete=message["id"])
        else:
            raise ValueError("Unknown message type")
