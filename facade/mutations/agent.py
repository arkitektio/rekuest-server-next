from kante.types import Info
import strawberry
from facade import types, models, inputs, scalars
import logging

logger = logging.getLogger(__name__)


@strawberry.input
class AgentInput:
    instance_id: scalars.InstanceID = strawberry.field(
        description="The instance ID of the agent. This is used to identify the agent in the system."
    )
    name: str | None = strawberry.field(
        default=None,
        description="The name of the agent. This is used to identify the agent in the system.",
    )
    extensions: list[str] | None = strawberry.field(
        default=None,
        description="The extensions of the agent. This is used to identify the agent in the system.",
    )
    # Hook Agent Fields for Server-to-Server Communication
    is_hook_agent: bool = strawberry.field(
        default=False,
        description="If true, this agent will receive tasks via HTTP POST instead of WebSocket.",
    )
    hook_endpoint: str | None = strawberry.field(
        default=None,
        description="The HTTP endpoint to send task assignments to for hook agents.",
    )
    hook_secret_token: str | None = strawberry.field(
        default=None,
        description="Secret token used to authenticate requests to hook agent endpoint.",
    )


@strawberry.input
class DeleteAgentInput:
    id: strawberry.ID = strawberry.field(
        description="The ID of the agent to delete. This is used to identify the agent in the system."
    )


async def ensure_agent(info: Info, input: AgentInput) -> types.Agent:
    # TODO: Hasch this
    
    registry, _ = await models.Registry.objects.aupdate_or_create(
        client=info.context.request.client,
        user=info.context.request.user,
    )
    
    # Validate hook agent parameters
    if input.is_hook_agent:
        if not input.hook_endpoint:
            raise ValueError("hook_endpoint is required for hook agents")
        if not input.hook_secret_token:
            raise ValueError("hook_secret_token is required for hook agents")

    defaults = {
        "name": input.name or f"{str(registry.id)} on {input.instance_id}",
        "extensions": input.extensions,
        "is_hook_agent": input.is_hook_agent,
    }
    
    # Only set hook fields for hook agents
    if input.is_hook_agent:
        defaults["hook_endpoint"] = input.hook_endpoint
        defaults["hook_secret_token"] = input.hook_secret_token

    agent, _ = await models.Agent.objects.aupdate_or_create(
        registry=registry,
        instance_id=input.instance_id or "default",
        defaults=defaults,
    )

    memory_shelve, _ = await models.MemoryShelve.objects.aget_or_create(
        agent=agent,
        defaults=dict(
            name=f"{str(agent)} memory shelve",
            creator=info.context.request.user,
        ),
    )

    async for drawer in models.MemoryDrawer.objects.filter(
        shelve=memory_shelve,
    ):
        await drawer.adelete()

    return agent


def pin_agent(info, input: inputs.PinInput) -> types.Agent:
    
    agent = models.Agent.objects.get(id=input.id)
    if input.pin:
        agent.pinned_by.add(info.context.request.user)
    else:
        agent.pinned_by.remove(info.context.request.user)
    agent.save()
    return agent


def delete_agent(info, input: DeleteAgentInput) -> strawberry.ID:
    agent = models.Agent.objects.get(id=input.id)
    agent.delete()
    return input.id
