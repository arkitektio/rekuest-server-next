from strawberry.dataloader import DataLoader
from facade import models

PKType = int | str


async def load_agents_by_ids(ids: list[PKType]) -> list[models.Agent | None]:
    # 1. Fetch all matching agents in a single query (batching)
    agents_qs = models.Agent.objects.filter(id__in=ids)

    # 2. Map the results into a dictionary by ID.
    # Casting to string ensures we don't get misses if inputs are a mix of int/str
    agent_map = {str(agent.pk): agent async for agent in agents_qs}

    # 3. Return the agents mapped to the exact order of the input `ids`.
    # Any requested ID not found in the DB will return None, keeping the array length consistent.
    return [agent_map.get(str(i)) for i in ids]


async def load_implementations_by_ids(ids: list[PKType]) -> list[models.Implementation | None]:
    # 1. Fetch all matching implementations in a single query (batching)
    impl_qs = models.Implementation.objects.filter(id__in=ids)

    # 2. Map the results into a dictionary by ID.
    # Casting to string ensures we don't get misses if inputs are a mix of int/str
    impl_map = {str(impl.pk): impl async for impl in impl_qs}

    # 3. Return the implementations mapped to the exact order of the input `ids`.
    # Any requested ID not found in the DB will return None, keeping the array length consistent.
    return [impl_map.get(str(i)) for i in ids]


agent_loader = DataLoader(load_fn=load_agents_by_ids)
implementation_loader = DataLoader(load_fn=load_implementations_by_ids)
