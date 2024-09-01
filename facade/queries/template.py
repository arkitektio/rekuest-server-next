from typing import List

import strawberry
from facade import filters, models, scalars, types
from kante.types import Info


def template_at(
    info: Info,
    agent: strawberry.ID,
    extension: str | None = None,
    interface: str | None = None,
    node_hash: str | None = None,
) -> types.Template:
    if node_hash:
        return models.Template.objects.get(agent_id=agent, node__hash=node_hash)
    
    return models.Template.objects.get(agent_id=agent, extension=extension, interface=interface)



async def my_template_at(
    info: Info,
    instance_id: str, 
    node_id: strawberry.ID | None = None,
    interface: str | None = None,
) -> types.Template:
    
    # TODO: Hasch this
    registry, _ = await models.Registry.objects.aget_or_create(
        app=info.context.request.app,
        user=info.context.request.user,
    )

    agent, _ = await models.Agent.objects.aget_or_create(
        registry=registry,
        instance_id=instance_id,
    )
    
    if node_id:
        return await models.Template.objects.aget(agent=agent, node_id=node_id)
    
    if interface:
        return await models.Template.objects.aget(agent=agent, interface=interface)
    
    raise ValueError("Either node_id or interface must be provided")
    