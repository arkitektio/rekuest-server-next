from typing import List
from facade import filters, models, scalars, types
from kante.types import Info
import strawberry

def state_for(
    info: Info,
    template: strawberry.ID | None = None,
    agent: strawberry.ID | None = None,
    state_hash: str | None = None,
) -> types.State:
    
    if agent:
        agent = models.Agent.objects.get(id=agent)
    elif template: 
        agent = models.Template.objects.get(id=template).agent
    else:
        raise ValueError("Either agent or template must be provided")

    return models.State.objects.get(agent=agent, state_schema__hash=state_hash)
    