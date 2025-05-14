from kante.types import Info
from facade import types, models, inputs, unique
import logging
import jsonpatch
import strawberry


logger = logging.getLogger(__name__)


def underscore(s: str) -> str:
    return s.replace(" ", "_").replace("-", "_").lower()


async def set_state(info: Info, input: inputs.SetStateInput) -> types.State:
    user = info.context.request.user
    client = info.context.request.client

    registry, _ = await models.Registry.objects.aget_or_create(
        client=client,
        user=user,
    )

    agent, _ = await models.Agent.objects.aget_or_create(
        registry=registry,
        instance_id=input.instance_id or "default",
        defaults=dict(
            name=f"{str(registry.id)} on {input.instance_id}",
        ),
    )

    state, _ = await models.State.objects.aupdate_or_create(
        interface=input.interface,
        agent=agent,
        defaults=dict(
            value=input.value,
        ),
    )

    return state


def update_state(info: Info, input: inputs.UpdateStateInput) -> types.State:
   

    registry, _ = models.Registry.objects.get_or_create(
        client=info.context.request.client,
        user=info.context.request.user,
    )

    agent, _ = models.Agent.objects.get_or_create(
        registry=registry,
        instance_id=input.instance_id or "default",
        defaults=dict(
            name=f"{str(registry.id)} on {input.instance_id}",
        ),
    )

    state = models.State.objects.get(interface=input.interface, agent=agent)

    old_state = state.value

    patch = jsonpatch.JsonPatch([i for i in input.patches])

    new_state = patch.apply(old_state)

    state.value = new_state

    state.save()

    return state


async def archive_state(info: Info, input: inputs.ArchiveStateInput) -> types.State:
    

    registry, _ = await models.Registry.objects.aget_or_create(
        client=info.context.request.client,
        user=info.context.request.user,
    )
    agent, _ = await models.Agent.objects.aget_or_create(
        registry=registry,
        instance_id=input.instance_id or "default",
        defaults=dict(
            name=f"{str(registry.id)} on {input.instance_id}",
        ),
    )

    state = await models.State.objects.aget(
        state_schema_id=input.state_schema, agent=agent
    )

    historical_state = await models.HistoricalState.objects.create(
        state=state,
        value=state.value,
    )

    return historical_state.state



def set_agent_states(
    info: Info, input: inputs.SetAgentStatesInput
) -> list[types.State]:
    user = info.context.request.user
    client = info.context.request.client

    registry, _ = models.Registry.objects.get_or_create(
        client=client,
        user=user,
    )

    agent, _ = models.Agent.objects.get_or_create(
        registry=registry,
        instance_id=input.instance_id or "default",
        defaults=dict(
            name=f"{str(registry.id)} on {input.instance_id}",
        ),
    )

    states = []
    
    previous_states_id = models.State.objects.filter(
        agent=agent
    ).values("id").all()

    new_state_id = []
    created_implementations = []
    
    for inputstate in input.implementations:
        state_schema, _ = models.StateSchema.objects.update_or_create(
            hash=unique.hash_state_schema(inputstate.state_schema),
            defaults=dict(
                name=inputstate.state_schema.name,
                ports=[strawberry.asdict(i) for i in inputstate.state_schema.ports],
                description="A state schema",
            ),
        )

        
        state, _ = models.State.objects.update_or_create(
            interface=inputstate.interface,
            agent=agent,
            defaults=dict(
                
                state_schema=state_schema,
                value=inputstate.initial,
            ),
        )
        
        new_state_id.append(state.id)
        states.append(state)


    for i in previous_states_id:
        if i["id"] not in new_state_id:
            state = models.State.objects.get(id=i["id"])
            state.delete()

    return states
