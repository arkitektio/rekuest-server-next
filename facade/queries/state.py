from facade import models, types, inputs, managers
from kante.types import Info
import strawberry


def state_for(
    info: Info,
    agent: strawberry.ID,
    state_hash: str | None = None,
    demand: inputs.SchemaDemandInput | None = None,
) -> types.State:
    agent = models.Agent.objects.get(id=agent)

    if demand:
        if demand.matches:
            state_ids = managers.get_state_ids_by_demands(demand.matches)

        return models.State.objects.get(agent=agent, id__in=state_ids)

    if state_hash:
        return models.State.objects.get(agent=agent, state_schema__hash=state_hash)

    raise ValueError("Either state_hash or demand must be provided")
