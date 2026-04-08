import uuid

from kante.types import Info
from facade.mutations.implementation import _create_implementation
import strawberry
from facade import types, models, inputs, scalars
from rekuest_core.inputs.types import StructureInput, InterfaceInput, ImplementationInput, LockImplementationInput, StateImplementationInput
from rekuest_core.inputs.models import ImplementationInputModel, StateImplementationInputModel, LockImplementationInputModel
import logging
from facade import types, models, inputs, unique
from pydantic import BaseModel
import kante

logger = logging.getLogger(__name__)


@strawberry.input
class AgentInput:
    instance_id: scalars.InstanceId = strawberry.field(description="The instance ID of the agent. This is used to identify the agent in the system.")
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
        instance_id=input.instance_id or "default",
        defaults=dict(
            name=input.name or f"{str(registry.pk)} on {input.instance_id}",
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
    instance_id: str
    name: str | None = None
    extensions: list[str] | None = None
    states: list[StateImplementationInputModel] | None = None
    implementations: list[ImplementationInputModel] | None = None
    locks: list[LockImplementationInputModel] | None = None
    hash: str | None = None
    pass


@kante.pydantic_input(ImplementAgentInputModel, description="Implement an agent with the given implementations, states and locks. This will create the agent if it doesn't exist and update it if it does exist.")
class ImplementAgentInput:
    instance_id: scalars.InstanceId = strawberry.field(description="The instance ID of the agent. This is used to identify the agent in the system.")
    name: str | None = strawberry.field(
        default=None,
        description="The name of the agent. This is used to identify the agent in the system.",
    )
    extensions: list[str] | None = strawberry.field(
        default=None,
        description="The extensions of the agent. This is used to identify the agent in the system.",
    )
    locks: list[LockImplementationInput] | None = strawberry.field(
        default=None,
        description="The locks of the agent. This is used to specify which resources the agent needs to run",
    )
    states: list[StateImplementationInput] | None = strawberry.field(
        default=None,
        description="The states of the agent. This is used to specify the initial states of the agent",
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
        instance_id=input.instance_id or "default",
        defaults=dict(
            name=input.name or f"{str(registry.pk)} on {input.instance_id}",
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

    return agent


def pin_agent(info: Info, input: inputs.PinInput) -> types.Agent:
    agent = models.Agent.objects.get(id=input.id)
    if input.pin:
        agent.pinned_by.add(info.context.request.user)
    else:
        agent.pinned_by.remove(info.context.request.user)
    agent.save()
    return agent


def delete_agent(info: Info, input: DeleteAgentInput) -> strawberry.ID:
    agent = models.Agent.objects.get(id=input.id)
    agent.delete()
    return input.id
