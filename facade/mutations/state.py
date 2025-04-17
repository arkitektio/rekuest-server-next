from kante.types import Info
import strawberry_django
import strawberry
from facade import types, models, inputs, enums, scalars, channels
from facade.channels import new_state_broadcast
import logging
import jsonpatch

logger = logging.getLogger(__name__)


def underscore(s: str) -> str:
    return s.replace(" ", "_").replace("-", "_").lower()


async def set_state(info: Info, input: inputs.SetStateInput) -> types.State:

    registry, _ = await models.Registry.objects.aget_or_create(
        app=info.context.request.app,
        user=info.context.request.user,
    )

    agent, _ = await models.Agent.objects.aget_or_create(
        registry=registry,
        instance_id=input.instance_id or "default",
        defaults=dict(
            name=f"{str(registry.id)} on {input.instance_id}",
        ),
    )

    state, _ = await models.State.objects.aupdate_or_create(
        state_schema_id=input.state_schema,
        agent=agent,
        defaults=dict(
            value=input.value,
        ),
    )

    return state


def update_state(info: Info, input: inputs.UpdateStateInput) -> types.State:

    registry, _ = models.Registry.objects.get_or_create(
        app=info.context.request.app,
        user=info.context.request.user,
    )

    agent, _ = models.Agent.objects.get_or_create(
        registry=registry,
        instance_id=input.instance_id or "default",
        defaults=dict(
            name=f"{str(registry.id)} on {input.instance_id}",
        ),
    )

    state = models.State.objects.get(state_schema_id=input.state_schema, agent=agent)

    old_state = state.value

    patch = jsonpatch.JsonPatch([i for i in input.patches])

    new_state = patch.apply(old_state)

    state.value = new_state

    state.save()
    logging.info(f"UPDATING STATE {state.id}")
    new_state_broadcast(state.id, [f"new_state_stuff{state.id}", "farticarti"])

    return state


def archive_state(info: Info, input: inputs.ArchiveStateInput) -> types.State:

    registry, _ = models.Registry.objects.aget_or_create(
        app=info.context.request.app,
        user=info.context.request.user,
    )

    agent, _ = models.Agent.objects.aget_or_create(
        registry=registry,
        instance_id=input.instance_id or "default",
        defaults=dict(
            name=f"{str(registry.id)} on {input.instance_id}",
        ),
    )

    state = models.State.objects.get(state_schema_id=input.state_schema, agent=agent)

    historical_state = models.HistoricalState.objects.create(
        state=state,
        value=state.value,
    )

    return historical_state.state
