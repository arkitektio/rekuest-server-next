from kante.types import Info
import strawberry
from facade import types, models, scalars
from rekuest_core import scalars as rscalars
from authentikate.vars import get_user, get_client


@strawberry.input
class ShelveInMemoryDrawerInput:
    instance_id: scalars.InstanceID = strawberry.field(
        description="The instance ID of the agent. This is used to identify the agent in the system."
    )
    identifier: rscalars.Identifier = strawberry.field(
        description="The identifier of the drawer. This is used to identify the drawer in the system."
    )
    resource_id: str = strawberry.field(description="The resource ID of the drawer.")
    label: str | None = strawberry.field(
        default=None,
        description="The label of the drawer. This is used to identify the drawer in the system.",
    )
    description: str | None = strawberry.field(
        default=None,
        description="The description of the drawer. This is used to identify the drawer in the system.",
    )


def shelve_in_memory_drawer(
    info: Info, input: ShelveInMemoryDrawerInput
) -> types.MemoryDrawer:

    registry, _ = models.Registry.objects.update_or_create(client=info.context.request.client, user=info.context.request.user)

    agent, _ = models.Agent.objects.update_or_create(
        registry=registry,
        instance_id=input.instance_id or "default",
        defaults=dict(
            name=f"{str(registry)} on {input.instance_id}",
        ),
    )
    
    memory_shelve, _ = models.MemoryShelve.objects.get_or_create(
        agent=agent,
        defaults=dict(
            name=f"{str(agent)} memory shelve",
            creator=info.context.request.user,
        ),
    )

    x, _ = models.MemoryDrawer.objects.update_or_create(
        shelve=memory_shelve,
        resource_id=input.resource_id,
        defaults=dict(
            label=input.label,
            description=input.description,
            identifier=input.identifier,
        ),
    )

    return x


@strawberry.input
class UnshelveMemoryDrawerInput:
    instance_id: scalars.InstanceID = strawberry.field(
        description="The instance ID of the agent. This is used to identify the agent in the system."
    )
    id: str = strawberry.field(description="The resource ID of the drawer.")


def unshelve_memory_drawer(
    info: Info, input: UnshelveMemoryDrawerInput
) -> strawberry.ID:

    registry, _ = models.Registry.objects.update_or_create(
        client=info.context.request.client, user=info.context.request.user
    )

    agent, _ = models.Agent.objects.update_or_create(
        registry=registry,
        instance_id=input.instance_id or "default",
        defaults=dict(
            name=f"{str(registry)} on {input.instance_id}",
        ),
    )
    
    
    x = models.MemoryDrawer.objects.get(
        id=input.id,
    )
    
    if x.shelve != agent.memory_shelve:
        raise Exception("This drawer does not belong to this agent.")

    id = str(x.id)

    x.delete()

    return id
