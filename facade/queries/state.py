from typing import List
from facade import filters, models, scalars, types
from kante.types import Info
import strawberry

def state_for(
    info: Info,
    template: strawberry.ID | None = None,
    agent: strawberry.ID | None = None,
    state_key: str | None = None,
) -> types.State:
    
    if agent:
        agent = models.Agent.objects.get(id=agent)
    elif template: 
        agent = models.Template.objects.get(id=template).agent
    else:
        agent = None


    return models.StateSchema.objects.get(agent=agent, name=state_key).states.first()
    