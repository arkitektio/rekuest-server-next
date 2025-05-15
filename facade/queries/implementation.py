import strawberry
from facade import models, types, inputs, managers
from kante.types import Info


def implementation_at(
    info: Info,
    agent: strawberry.ID,
    extension: str | None = None,
    interface: str | None = None,
    action_hash: str | None = None,
    demand: inputs.ActionDemandInput | None = None,
) -> types.Implementation:
    if action_hash:
        return models.Implementation.objects.get(agent_id=agent, action__hash=action_hash)

    if demand:
        action_ids = managers.get_action_ids_by_action_demand(demand)
        return models.Implementation.objects.get(agent_id=agent, action_id__in=action_ids)

    return models.Implementation.objects.get(agent_id=agent, extension=extension, interface=interface)


async def my_implementation_at(
    info: Info,
    instance_id: str,
    action_id: strawberry.ID | None = None,
    interface: str | None = None,
) -> types.Implementation:
    # TODO: Hasch this

    registry, _ = await models.Registry.objects.aget_or_create(
        client=info.context.request.client,
        user=info.context.request.user,
    )

    agent, _ = await models.Agent.objects.aget_or_create(
        registry=registry,
        instance_id=instance_id,
    )

    if action_id:
        return await models.Implementation.objects.aget(agent=agent, action_id=action_id)

    if interface:
        return await models.Implementation.objects.aget(agent=agent, interface=interface)

    raise ValueError("Either action_id or interface must be provided")
