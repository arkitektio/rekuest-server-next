import uuid
from random import choice
from typing import Protocol

from facade import enums, inputs, models, types, messages
from facade.consumers.async_consumer import AgentConsumer
from kante.types import Info
from authentikate.vars import get_user, get_client
import logging


class ControllBackend(Protocol):
    def create_message_id(self) -> str: ...

    def interrupt(
        self, info: Info, input: inputs.InterruptInputModel
    ) -> types.Assignation: ...

    def reserve(
        self, info: Info, input: inputs.ReserveInputModel
    ) -> types.Reservation: ...

    def cancel(
        self, info: Info, input: inputs.CancelInputModel
    ) -> types.Assignation: ...

    def assign(
        self, info: Info, input: inputs.AssignInputModel
    ) -> types.Assignation: ...

    def resume(
        self, info: Info, input: inputs.ResumeInputModel
    ) -> types.Assignation: ...

    def pause(self, info: Info, input: inputs.PauseInputModel) -> types.Assignation: ...


def get_waiter_for_context(info: Info, instance_id: str) -> None:
    # TODO: HASH THIS FOR EASIER RETRIEVAL
    

    registry, _ = models.Registry.objects.get_or_create(client=info.context.request.client, user=info.context.request.user)

    waiter, _ = models.Waiter.objects.get_or_create(
        registry=registry, instance_id=instance_id, defaults=dict(name="default")
    )
    return waiter


class RedisControllBackend(ControllBackend):
    def create_message_id(self) -> str:
        return str(uuid.uuid4())

    def interrupt(self, input: inputs.InterruptInputModel) -> models.Assignation:
        parent = models.Assignation.objects.get(id=input.assignation)
        parent.status = enums.AssignationEventKind.INTERUPTED
        parent.save()

        AgentConsumer.broadcast(
            parent.implementation.agent.id,
            messages.Interrupt(
                assignation=parent.id,
            ),
        )

        children = models.Assignation.objects.filter(parent_id=input.assignation).all()

        for child in children:
            child.status = enums.AssignationEventKind.INTERUPTED
            child.save()

            AgentConsumer.broadcast(
                child.implementation.agent.id,
                messages.Interrupt(
                    assignation=child.id,
                ),
            )

        return parent

    def reserve(
        self, info: Info, input: inputs.ReserveInputModel
    ) -> models.Reservation:
        if input.action is None and input.implementation is None:
            raise ValueError("Either action or implementation must be provided")

        if input.implementation:
            # We provided a implementation and are creating a reservation with just that
            # implementation
            implementation = models.Implementation.objects.get(id=input.implementation)
            action = implementation.action
            implementations = [implementation]
        if input.action:
            # We provided a action and are creating a reservation with all implementations
            # for that action at this time
            action = models.Action.objects.get(id=input.action)
            implementations = models.Implementation.objects.filter(action=action).all()
            if len(implementations) == 0:
                raise ValueError(
                    "No implementations found for this action. Cannot reserve."
                )

        waiter = get_waiter_for_context(info, input.instance_id)

        res, created = models.Reservation.objects.update_or_create(
            reference=input.reference,
            waiter=waiter,
            defaults=dict(
                title=input.title,
                binds=input.binds.dict() if input.binds else None,
                causing_assignation_id=input.assignation_id,
                action=action,
                strategy=enums.ReservationStrategy.ROUND_ROBIN,
            ),
        )

        # TODO: Find really the best fitting provision

        res.implementations.set(implementations)

        # TODO: Cache the reservation in the redis cache and make it available for the assignation

        return res

    def cancel(self, input: inputs.CancelInputModel) -> models.Assignation:
        assignation = models.Assignation.objects.get(id=input.assignation)
        assignation.status = enums.AssignationStatus.CANCELLED
        assignation.save()

        AgentConsumer.broadcast(
            assignation.agent.id,
            message=messages.Cancel(
                assignation=str(assignation.id),
            ),
        )
        return assignation

    def assign(self, info: Info, input: inputs.AssignInputModel) -> models.Assignation:
        # TODO: Check if function is cached and was

        reservation = None
        action = None
        implementation = None
        agent = None

        waiter = get_waiter_for_context(info, input.instance_id)

        if input.reservation:
            # TODO: Retrieve the reservation in the redis cache wth the provision keys set
            reservation = models.Reservation.objects.prefetch_related("provisions").get(
                id=input.reservation
            )
            action = reservation.action
            implementation = choice(reservation.implementations.all())
            if not implementation:
                raise ValueError("No implementation matchable for this reservation")
            agent = implementation.agent

        elif input.action:
            reservation = None
            action = models.Action.objects.get(id=input.action)
            implementation = models.Implementation.objects.filter(
                action=action, agent__connected=True
            ).first()
            if not implementation:
                raise ValueError("No active implementation found for this action")

            agent = implementation.agent

        elif input.implementation:
            reservation = None
            implementation = models.Implementation.objects.get(id=input.implementation)
            action = implementation.action
            agent = implementation.agent

        elif input.action_hash:
            reservation = None
            action = models.Action.objects.filter(hash=input.action_hash).first()
            implementation = models.Implementation.objects.filter(
                action=action, agent__connected=True
            ).first()
            if not implementation:
                raise ValueError("No active implementation found for this action")
            agent = implementation.agent

        elif input.interface:
            reservation = None
            implementation = models.Implementation.objects.get(id=input.implementation)
            action = implementation.action
            agent = implementation.agent

        else:
            raise ValueError(
                "You need to provide either, action_hash or action_id, to create an assignment for an agent"
            )

        reference = input.reference or self.create_message_id()

        assignation = models.Assignation.objects.create(
            reservation=reservation,
            action=action,
            args=input.args,
            reference=reference,
            parent_id=input.parent,
            agent=agent,
            implementation=implementation,
            is_done=False,
            latest_event_kind=enums.AssignationEventKind.ASSIGN,
            latest_instruct_kind=enums.AssignationInstructKind.ASSIGN,
            hooks=input.hooks or [],
            waiter=waiter,
            ephemeral=input.ephemeral,
        )

        AgentConsumer.broadcast(
            assignation.agent.id,
            message=messages.Assign(
                assignation=str(assignation.id),
                args=input.args,
                reference=reference,
                interface=implementation.interface,
                extension=implementation.extension,
                action=str(action.id),
            ),
        )
        if input.hooks:
            for hook in input.hooks:
                if hook.kind == enums.HookKind.INIT:
                    # recursive assign
                    self.assign(
                        inputs.AssignInputModel(
                            action_hash=hook.hash,
                            parent=assignation.id,
                            args={"assignation": assignation.id},
                            reference="init_hook_0",
                        )
                    )

        return assignation

    def resume(self, info: Info, input: inputs.ResumeInputModel) -> models.Assignation:
        assignation = models.Assignation.objects.get(id=input.assignation)
        assignation.status = enums.AssignationStatus.RESUME
        assignation.save()

        AgentConsumer.broadcast(
            assignation.agent.id,
            message=messages.Cancel(
                assignation=assignation.id,
            ),
        )
        return assignation

    def collect(self, info: Info, input: inputs.CollectInputModel) -> list[str]:
        agents = {}
        for i in input.drawers:
            assert ":" in i, "Invalid drawer format"
            agent_id, drawer = i.split(":")
            agents.setdefault(agent_id, set()).add(i)

        for agent_id, drawers in agents.items():
            agent = models.Agent.objects.get(id=agent_id)
            logging.info(f"collecting {drawers} from agent {agent_id}")
            AgentConsumer.broadcast(
                agent.id,
                message=messages.Collect(
                    drawers=list(drawers),
                ),
            )

        return input.drawers

    def step(self, info: Info, input: inputs.StepInputModel) -> models.Assignation:
        assignation = models.Assignation.objects.get(id=input.assignation)
        assignation.status = enums.AssignationStatus.STEP
        assignation.save()

        AgentConsumer.broadcast(
            assignation.agent.id,
            message=messages.Cancel(
                assignation=assignation.id,
            ),
        )
        return assignation


controll_backend = RedisControllBackend()
