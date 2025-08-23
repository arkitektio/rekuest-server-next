from datetime import datetime, timedelta, timezone
import uuid
import asyncio
from random import choice
from typing import Protocol

from facade import enums, inputs, models, types, messages
from facade.consumers.async_consumer import AgentConsumer
from facade.hook_agent_service import hook_agent_service
from kante.types import Info
from authentikate.vars import get_user, get_client
import logging


class ControllBackend(Protocol):
    def create_message_id(self) -> str: ...

    def interrupt(self, info: Info, input: inputs.InterruptInputModel) -> types.Assignation: ...

    def reserve(self, info: Info, input: inputs.ReserveInputModel) -> types.Reservation: ...

    def cancel(self, info: Info, input: inputs.CancelInputModel) -> types.Assignation: ...

    def assign(self, info: Info, input: inputs.AssignInputModel) -> types.Assignation: ...

    def resume(self, info: Info, input: inputs.ResumeInputModel) -> types.Assignation: ...

    def pause(self, info: Info, input: inputs.PauseInputModel) -> types.Assignation: ...


def get_waiter_for_context(info: Info, instance_id: str) -> None:
    # TODO: HASH THIS FOR EASIER RETRIEVAL

    registry, _ = models.Registry.objects.get_or_create(client=info.context.request.client, user=info.context.request.user)

    waiter, _ = models.Waiter.objects.get_or_create(registry=registry, instance_id=instance_id, defaults=dict(name="default"))
    return waiter


class RedisControllBackend(ControllBackend):
    def create_message_id(self) -> str:
        return str(uuid.uuid4())

    def interrupt(self, input: inputs.InterruptInputModel) -> models.Assignation:
        parent = models.Assignation.objects.get(id=input.assignation)
        parent.status = enums.AssignationEventKind.INTERUPTED
        parent.save()

        # Send interrupt to parent agent - create task to handle async HTTP call
        asyncio.create_task(
            self._send_interrupt_to_agent(
                agent=parent.implementation.agent,
                message=messages.Interrupt(
                    assignation=parent.id,
                ),
            )
        )

        children = models.Assignation.objects.filter(parent_id=input.assignation).all()

        for child in children:
            child.status = enums.AssignationEventKind.INTERUPTED
            child.save()

            # Send interrupt to child agent - create task to handle async HTTP call
            asyncio.create_task(
                self._send_interrupt_to_agent(
                    agent=child.implementation.agent,
                    message=messages.Interrupt(
                        assignation=child.id,
                    ),
                )
            )

        return parent

    def reserve(self, info: Info, input: inputs.ReserveInputModel) -> models.Reservation:
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
                raise ValueError("No implementations found for this action. Cannot reserve.")

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
        assignation.latest_event_kind = enums.AssignationStatus.CANCELLED
        assignation.save()

        # Send cancellation to agent - create task to handle async HTTP call without blocking
        asyncio.create_task(
            self._send_cancellation_to_agent(
                agent=assignation.agent,
                message=messages.Cancel(
                    assignation=str(assignation.id),
                ),
            )
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
            # this should be done in the redis cache to allow for super fast retrieval, 
            # especially when using the ephemeral flag
            reservation = models.Reservation.objects.prefetch_related("provisions").get(id=input.reservation)
            action = reservation.action
            implementation = choice(reservation.implementations.all())
            if not implementation:
                raise ValueError("No implementation matchable for this reservation")
            agent = implementation.agent

        elif input.action:
            reservation = None
            action = models.Action.objects.get(id=input.action)
            implementation = models.Implementation.objects.filter(
                action=action,
                agent__connected=True,
                agent__last_seen__gt=datetime.now() - timedelta(minutes=1)
            ).first()
            if not implementation:
                raise ValueError("No active implementation found for this action")

            agent = implementation.agent

        elif input.implementation:
            reservation = None
            implementation = models.Implementation.objects.get(id=input.implementation)
            action = implementation.action
            agent = implementation.agent
            assert agent.connected, "Agent is not connected"
            assert agent.last_seen > datetime.now(timezone.utc) - timedelta(minutes=1), "Agent is not connected"
            
            

        elif input.action_hash:
            reservation = None
            action = models.Action.objects.filter(hash=input.action_hash).first()
            implementation = models.Implementation.objects.filter(action=action, agent__connected=True).first()
            if not implementation:
                raise ValueError("No active implementation found for this action")
            agent = implementation.agent

        elif input.interface:
            reservation = None
            implementation = models.Implementation.objects.get(id=input.implementation)
            action = implementation.action
            agent = implementation.agent

        else:
            raise ValueError("You need to provide either, action_hash or action_id, to create an assignment for an agent")

        reference = input.reference or self.create_message_id()

        # TODO: if ephemeral is set, we should not store the assignation in the database
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

        # Send assignment to agent - check if it's a hook agent or regular WebSocket agent
        # Create task to handle async HTTP call without blocking
        asyncio.create_task(
            self._send_assignment_to_agent(
                agent=assignation.agent,
                message=messages.Assign(
                    assignation=str(assignation.id),
                    args=input.args,
                    user=str(info.context.request.user.id),
                    app=str(info.context.request.client.id),
                    reference=reference,
                    interface=implementation.interface,
                    extension=implementation.extension,
                    action=str(action.id),
                ),
            )
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

        # Send cancellation to agent - create task to handle async HTTP call
        asyncio.create_task(
            self._send_cancellation_to_agent(
                agent=assignation.agent,
                message=messages.Cancel(
                    assignation=assignation.id,
                ),
            )
        )
        return assignation

    def collect(self, info: Info, input: inputs.CollectInputModel) -> list[str]:
        agents = {}

        drawers = models.MemoryDrawer.objects.filter(id__in=input.drawers).prefetch_related("shelve__agent").all()

        for drawer in drawers:
            if drawer.shelve.agent.id not in agents:
                agents[drawer.shelve.agent.id] = set()
            agents[drawer.shelve.agent.id].add(str(drawer.id))

        for agent_id, drawers in agents.items():
            agent = models.Agent.objects.get(id=agent_id)
            logging.info(f"collecting {drawers} from agent {agent_id}")
            # Send collect to agent - create task to handle async HTTP call
            asyncio.create_task(
                self._send_collect_to_agent(
                    agent=agent,
                    message=messages.Collect(
                        drawers=list(drawers),
                    ),
                )
            )

        return input.drawers

    def step(self, info: Info, input: inputs.StepInputModel) -> models.Assignation:
        assignation = models.Assignation.objects.get(id=input.assignation)
        assignation.status = enums.AssignationStatus.STEP
        assignation.save()

        # Send cancellation to agent - create task to handle async HTTP call
        asyncio.create_task(
            self._send_cancellation_to_agent(
                agent=assignation.agent,
                message=messages.Cancel(
                    assignation=assignation.id,
                ),
            )
        )
        return assignation

    async def _send_assignment_to_agent(self, agent: models.Agent, message: messages.Assign) -> bool:
        """
        Send assignment message to agent, routing to WebSocket or HTTP based on agent type.
        
        Args:
            agent: The agent to send the assignment to
            message: The assignment message to send
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if agent.is_hook_agent:
                # Send via HTTP POST to hook agent
                return await hook_agent_service.send_assignment_to_hook_agent(agent, message)
            else:
                # Send via WebSocket broadcast to regular agent
                AgentConsumer.broadcast(agent.id, message=message)
                return True
        except Exception as e:
            logging.error(f"Failed to send assignment to agent {agent.id}: {e}")
            return False

    async def _send_cancellation_to_agent(self, agent: models.Agent, message: messages.Cancel) -> bool:
        """
        Send cancellation message to agent, routing to WebSocket or HTTP based on agent type.
        
        Args:
            agent: The agent to send the cancellation to
            message: The cancellation message to send
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if agent.is_hook_agent:
                # Send via HTTP POST to hook agent
                return await hook_agent_service.send_cancellation_to_hook_agent(agent, message)
            else:
                # Send via WebSocket broadcast to regular agent
                AgentConsumer.broadcast(agent.id, message=message)
                return True
        except Exception as e:
            logging.error(f"Failed to send cancellation to agent {agent.id}: {e}")
            return False


    async def _send_interrupt_to_agent(self, agent: models.Agent, message: messages.Interrupt) -> bool:
        """
        Send interrupt message to agent, routing to WebSocket or HTTP based on agent type.
        
        Args:
            agent: The agent to send the interrupt to
            message: The interrupt message to send
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if agent.is_hook_agent:
                # Send via HTTP POST to hook agent
                return await hook_agent_service.send_interrupt_to_hook_agent(agent, message)
            else:
                # Send via WebSocket broadcast to regular agent
                AgentConsumer.broadcast(agent.id, message=message)
                return True
        except Exception as e:
            logging.error(f"Failed to send interrupt to agent {agent.id}: {e}")
            return False


    async def _send_collect_to_agent(self, agent: models.Agent, message: messages.Collect) -> bool:
        """
        Send collect message to agent, routing to WebSocket or HTTP based on agent type.
        
        Args:
            agent: The agent to send the collect to
            message: The collect message to send
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if agent.is_hook_agent:
                # Send via HTTP POST to hook agent
                return await hook_agent_service.send_collect_to_hook_agent(agent, message)
            else:
                # Send via WebSocket broadcast to regular agent
                AgentConsumer.broadcast(agent.id, message=message)
                return True
        except Exception as e:
            logging.error(f"Failed to send collect to agent {agent.id}: {e}")
            return False


controll_backend = RedisControllBackend()
