import uuid

from kante.types import Info
from facade.mutations.implementation import _create_implementation
import strawberry
from facade import types, models, inputs, scalars
from rekuest_core.inputs.types import BlokImplementationInput, StructureInput, InterfaceInput, ImplementationInput, LockImplementationInput, StateImplementationInput
from rekuest_core.inputs.models import BlokImplementationInputModel, ImplementationInputModel, StateImplementationInputModel, LockImplementationInputModel
import logging
from facade import types, models, inputs, unique
from pydantic import BaseModel
import kante

logger = logging.getLogger(__name__)


@strawberry.input
class AgentInput:
    name: str | None = strawberry.field(
        default=None,
        description="The name of the agent. This is used to identify the agent in the system.",
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

    agent, _ = models.Agent.objects.get_or_create(
        registry=registry,
        defaults=dict(
            name=input.name or f"{str(registry.pk)}",
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


class ImplementAgentInputModel(BaseModel):
    name: str | None = None
    states: list[StateImplementationInputModel] | None = None
    implementations: list[ImplementationInputModel] | None = None
    locks: list[LockImplementationInputModel] | None = None
    bloks: list[BlokImplementationInputModel] | None = None
    hash: str | None = None
    pass


@kante.pydantic_input(ImplementAgentInputModel, description="Implement an agent with the given implementations, states and locks. This will create the agent if it doesn't exist and update it if it does exist.")
class ImplementAgentInput:
    name: str | None = strawberry.field(
        default=None,
        description="The name of the agent. This is used to identify the agent in the system.",
    )
    locks: list[LockImplementationInput] | None = strawberry.field(
        default=None,
        description="The locks of the agent. This is used to specify which resources the agent needs to run",
    )
    states: list[StateImplementationInput] | None = strawberry.field(
        default=None,
        description="The states of the agent. This is used to specify the initial states of the agent",
    )
    bloks: list[BlokImplementationInput] | None = strawberry.field(
        default=None,
        description="The blocks of the agent. This is used to specify the initial blocks of the agent",
    )
    implementations: list[ImplementationInput] | None = strawberry.field(
        default=None,
        description="The implementations of the agent. This is used to specify the initial implementations of the agent",
    )
    hash: str | None = strawberry.field(
        default=None,
        description="A unique hash of the agent definition. An agent can use this hash to check if its definition has changed and if it needs to update its implementations and states. This is used to optimize the update process by only updating the implementations and states that have changed.",
    )


def implement_agent(info: Info, input: ImplementAgentInput) -> types.Agent:
    input = input.to_pydantic()

    registry, _ = models.Registry.objects.update_or_create(
        client=info.context.request.client,
        user=info.context.request.user,
        organization=info.context.request.organization,
    )

    agent, _ = models.Agent.objects.update_or_create(
        registry=registry,
        defaults=dict(
            name=input.name or f"{str(registry.pk)}",
            app=info.context.request.client.release.app,
            organization=info.context.request.organization,
            user=info.context.request.user,
            release=info.context.request.client.release,
            device=info.context.request.client.device,
            hash=input.hash or str(uuid.uuid4()),
        ),
    )

    previous_implementation_ids = models.Implementation.objects.filter(agent=agent).values("id").all()
    previous_states_id = models.State.objects.filter(agent=agent).values("id").all()

    created_implementations_id = []
    created_implementations = []
    created_states_id = []
    created_states = []

    for lock in input.locks or []:
        lock = models.Lock.objects.get_or_create(
            agent=agent,
            key=lock.key,
            defaults=dict(
                description=lock.definition.description,
            ),
        )

    for implementation in input.implementations or []:
        created_implementation = _create_implementation(implementation, agent)

        created_implementations_id.append(created_implementation.id)
        created_implementations.append(created_implementation)

    for inputstate in input.states or []:
        state_definition, _ = models.StateDefinition.objects.update_or_create(
            hash=unique.hash_state_definition(inputstate.definition),
            defaults=dict(
                name=inputstate.definition.name,
                ports=[i.model_dump() for i in inputstate.definition.ports],
                description="A state definition",
            ),
        )

        state, _ = models.State.objects.update_or_create(
            interface=inputstate.interface,
            agent=agent,
            defaults=dict(
                definition=state_definition,
            ),
        )

        created_states_id.append(state.id)
        created_states.append(state)

    for i in previous_states_id:
        if i["id"] not in created_states_id:
            state = models.State.objects.get(id=i["id"])
            state.delete()

    for i in previous_implementation_ids:
        if i["id"] not in created_implementations_id:
            implementation = models.Implementation.objects.get(id=i["id"])
            implementation.delete()

    for blok in input.bloks or []:
        catalog = models.UICatalog.objects.get_or_create(name=blok.catalog)[0] if blok.catalog else models.UICatalog.objects.get_or_create(name="default")[0]

        x, _ = models.Blok.objects.update_or_create(
            name=blok.key,
            defaults=dict(
                components=[x.model_dump() for x in blok.components] if blok.components else [],
                description=blok.description,
                creator=info.context.request.user,
                catalog=catalog,
                demo_state=blok.demo_state,
            ),
        )

        new_deps = []

        mblok, _ = models.MaterializedBlok.objects.update_or_create(
            blok=x,
        )

        if blok.dependencies:
            for i in blok.dependencies:
                dep, _ = models.BlokDependency.objects.update_or_create(
                    blok=x,
                    key=i.key,
                    defaults=dict(
                        action_demands=[x.model_dump() for x in i.action_demands] if i.action_demands else [],
                        state_demands=[x.model_dump() for x in i.state_demands] if i.state_demands else [],
                        app_filter=i.app,
                        version_filter=i.version,
                    ),
                )
                new_deps.append(dep)

                models.BlokAgentMapping.objects.update_or_create(
                    materialized_blok=mblok,
                    key=i.key,
                    dependency=dep,
                    defaults=dict(agent=agent),
                )

    return agent


def pin_agent(info: Info, input: inputs.PinInput) -> types.Agent:
    agent = models.Agent.objects.get(id=input.id)
    if input.pin:
        agent.pinned_by.add(info.context.request.user)
    else:
        agent.pinned_by.remove(info.context.request.user)
    agent.save()
    return agent


def update_agent(info: Info, input: inputs.UpdateAgentInput) -> types.Agent:
    agent = models.Agent.objects.get(id=input.id)
    if input.name is not None:
        agent.name = input.name
    agent.save()
    return agent


def delete_agent(info: Info, input: DeleteAgentInput) -> strawberry.ID:
    agent = models.Agent.objects.get(id=input.id)
    agent.delete()
    return input.id
