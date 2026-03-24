from kante.types import Info
import strawberry
from facade import types, models, inputs, scalars
from rekuest_core.inputs.types import StructureInput, InterfaceInput, LockSchemaInput

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
    locks: list[LockSchemaInput] | None = strawberry.field(
        default=None,
        description="The locks of the agent. This is used to specify which resources the agent needs to run",
    )


@strawberry.input
class DeleteAgentInput:
    id: strawberry.ID = strawberry.field(description="The ID of the agent to delete. This is used to identify the agent in the system.")


def ensure_agent(info: Info, input: AgentInput) -> types.Agent:
    # TODO: Hasch this

    registry, _ = models.Registry.objects.update_or_create(
        client=info.context.request.client,
        user=info.context.request.user,
        organization=info.context.request.organization,
    )

    agent, _ = models.Agent.objects.update_or_create(
        registry=registry,
        instance_id=input.instance_id or "default",
        defaults=dict(
            name=input.name or f"{str(registry.pk)} on {input.instance_id}",
            extensions=input.extensions or [],
            app=info.context.request.client.release.app,
            organization=info.context.request.organization,
            user=info.context.request.user,
            release=info.context.request.client.release,
            device=info.context.request.client.device,
        ),
    )

    memory_shelve, _ = models.MemoryShelve.objects.get_or_create(
        agent=agent,
        defaults=dict(
            name=f"{str(agent)} memory shelve",
            creator=info.context.request.user,
        ),
    )

    for drawer in models.MemoryDrawer.objects.filter(
        shelve=memory_shelve,
    ):
        drawer.delete()

    return agent


def pin_agent(info: Info, input: inputs.PinInput) -> types.Agent:
    agent = models.Agent.objects.get(id=input.id)
    if input.pin:
        agent.pinned_by.add(info.context.request.user)
    else:
        agent.pinned_by.remove(info.context.request.user)
    agent.save()
    return agent


def delete_agent(info: Info, input: DeleteAgentInput) -> strawberry.ID:
    agent = models.Agent.objects.get(id=input.id)
    agent.delete()
    return input.id
