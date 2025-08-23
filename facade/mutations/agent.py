from kante.types import Info
import strawberry
from facade import types, models, inputs, scalars, enums
import logging

logger = logging.getLogger(__name__)


@strawberry.input
class AgentInput:
    instance_id: scalars.InstanceId = strawberry.field(description="The instance ID of the agent. This is used to identify the agent in the system.")
    name: str | None = strawberry.field(
        default=None,
        description="The name of the agent. This is used to identify the agent in the system.",
    )
    extensions: list[str] | None = strawberry.field(
        default=None,
        description="The extensions of the agent. This is used to identify the agent in the system.",
    )
    kind: str | None = strawberry.field(
        default=None,
        description="The kind of agent (WEBSOCKET or WEBHOOK). Defaults to WEBSOCKET.",
    )
    hook_url: str | None = strawberry.field(
        default=None,
        description="The webhook URL for this agent (required if kind is WEBHOOK).",
    )
    hook_url_secret: str | None = strawberry.field(
        default=None,
        description="The webhook URL secret for this agent (required if kind is WEBHOOK).",
    )


@strawberry.input
class DeleteAgentInput:
    id: strawberry.ID = strawberry.field(description="The ID of the agent to delete. This is used to identify the agent in the system.")


async def ensure_agent(info: Info, input: AgentInput) -> types.Agent:
    # TODO: Hash this

    registry, _ = await models.Registry.objects.aupdate_or_create(
        client=info.context.request.client,
        user=info.context.request.user,
        organization=info.context.request.organization,
    )

    # Validate webhook agent requirements
    agent_kind = enums.AgentKind.WEBSOCKET  # Default
    if input.kind:
        if input.kind not in [kind.value for kind in enums.AgentKind]:
            raise ValueError(f"Invalid agent kind: {input.kind}. Must be one of: {[kind.value for kind in enums.AgentKind]}")
        agent_kind = enums.AgentKind(input.kind)
        
    if agent_kind == enums.AgentKind.WEBHOOK:
        if not input.hook_url:
            raise ValueError("hook_url is required for WEBHOOK agents")
        if not input.hook_url_secret:
            raise ValueError("hook_url_secret is required for WEBHOOK agents")

    agent_defaults = {
        "name": input.name or f"{str(registry.id)} on {input.instance_id}",
        "extensions": input.extensions or [],
        "kind": agent_kind.value,
    }

    # Add webhook-specific fields if provided
    if agent_kind == enums.AgentKind.WEBHOOK:
        agent_defaults["hook_url"] = input.hook_url
        agent_defaults["hook_url_secret"] = input.hook_url_secret

    agent, _ = await models.Agent.objects.aupdate_or_create(
        registry=registry,
        instance_id=input.instance_id or "default",
        defaults=agent_defaults,
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
