import uuid
from random import choice
from typing import Protocol

from facade import enums, inputs, models, types, messages
from facade.consumers.async_consumer import AgentConsumer
from kante.types import Info


class ControllBackend(Protocol):
    
    def create_message_id(self) -> str:
        ...

    def interrupt(self, info: Info, input: inputs.InterruptInputModel) -> types.Assignation:
        ...

    def reserve(self, info: Info, input: inputs.ReserveInputModel) -> types.Reservation:
        ...

    def cancel(self,info: Info, input: inputs.CancelInputModel) -> types.Assignation:
        ...

    def assign(self, info: Info, input: inputs.AssignInputModel) -> types.Assignation:
        ...

    def resume(self, info: Info, input: inputs.ResumeInputModel) -> types.Assignation:
        ...

    def pause(self, info: Info, input: inputs.PauseInputModel) -> types.Assignation:
        ...





def get_waiter_for_context(info: Info, instance_id: str) -> None:
    # TODO: HASH THIS FOR EASIER RETRIEVAL
    registry, _ = models.Registry.objects.get_or_create(
        app=info.context.request.app, user=info.context.request.user
    )

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
            parent.template.agent.id,
            messages.Interrupt(
                assignation=parent.id,
            )
        )
        
        
        children = models.Assignation.objects.filter(parent_id=input.assignation).all()
        
        for child in children:
            child.status = enums.AssignationEventKind.INTERUPTED
            child.save()

            AgentConsumer.broadcast(
                child.template.agent.id,
                messages.Interrupt(
                    assignation=child.id,
                )
            )
        
        
        
        return parent

    def reserve(self, info: Info, input: inputs.ReserveInputModel) -> models.Reservation:
        if input.node is None and input.template is None:
            raise ValueError("Either node or template must be provided")

        
        if input.template:
            # We provided a template and are creating a reservation with just that
            # template
            template = models.Template.objects.get(id=input.template)
            node = template.node
            templates = [template]
        if input.node:
            # We provided a node and are creating a reservation with all templates
            # for that node at this time
            node = models.Node.objects.get(id=input.node)
            templates = models.Template.objects.filter(node=node).all()
            if len(templates) == 0:
                raise ValueError("No templates found for this node. Cannot reserve.")
            
            

        waiter = get_waiter_for_context(info, input.instance_id)
        
        
        res, created = models.Reservation.objects.update_or_create(
            reference=input.reference,
            waiter=waiter,
            defaults=dict(
                title=input.title,
                binds=input.binds.dict() if input.binds else None,
                causing_assignation_id=input.assignation_id,
                node=node,
                strategy=enums.ReservationStrategy.ROUND_ROBIN,
            ),
        )

        # TODO: Find really the best fitting provision

        res.templates.set(templates)

        # TODO: Cache the reservation in the redis cache and make it available for the assignation

        return res

    def cancel(self, input: inputs.CancelInputModel) -> models.Assignation:
        assignation = models.Assignation.objects.get(id=input.assignation)
        assignation.status = enums.AssignationStatus.CANCELLED
        assignation.save()

        AgentConsumer.broadcast(
            assignation.agent.id,
            message=messages.Cancel(
                assignation=assignation.id,
            )
        )
        return assignation

    def assign(self, info: Info, input: inputs.AssignInputModel) -> models.Assignation:
        # TODO: Check if function is cached and was

        reservation = None
        node = None
        template = None
        agent = None

        waiter = get_waiter_for_context(info, input.instance_id)

        if input.reservation:
            # TODO: Retrieve the reservation in the redis cache wth the provision keys set
            reservation = models.Reservation.objects.prefetch_related("provisions").get(
                id=input.reservation
            )
            node = reservation.node
            template = choice(reservation.templates.all())
            if not template:
                raise ValueError("No template matchable for this reservation")
            agent = template.agent

        elif input.node:
            reservation = None
            node = models.Node.objects.get(id=input.node)
            template = models.Template.objects.filter(node=node, agent__connected=True).first()
            if not template:
                raise ValueError("No active template found for this node")
            
            agent = template.agent
            
        elif input.template:
            reservation = None
            template = models.Template.objects.get(id=input.template)
            node = template.node
            agent = template.agent
            
        elif input.node_hash:
            reservation = None
            node = models.Node.objects.filter(hash=input.node_hash).first()
            template = models.Template.objects.filter(node=node, agent__connected=True).first()
            if not template:
                raise ValueError("No active template found for this node")
            agent = template.agent
            
        elif input.interface:
            reservation = None
            template = models.Template.objects.get(id=input.template)
            node = template.node
            agent = template.agent

        else:
            raise ValueError(
                "You need to provide either, node_hash or node_id, to create an assignment for an agent"
            )


        reference = input.reference or self.create_message_id()

        assignation = models.Assignation.objects.create(
            reservation=reservation,
            node=node,
            args=input.args,
            reference=reference,
            parent_id=input.parent,
            agent=agent,
            template=template,
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
                assignation=assignation.id,
                args=input.args,
                reference=reference,
                interface=template.interface,
                extension=template.extension,
                node=node.id,
            ),
        )
        if input.hooks:
            for hook in input.hooks:
                if hook.kind == enums.HookKind.INIT:
                    # recursive assign
                    self.assign(
                        inputs.AssignInputModel(
                            node_hash=hook.hash,
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
            )
        )
        return assignation
    
    def collect(self, info: Info,  input: inputs.CollectInputModel) -> models.Assignation:
        assignation = models.Assignation.objects.get(id=input.assignation)
        assignation.status = enums.AssignationStatus.RESUME
        assignation.save()
        
        models.AssignationInstruct.objects.create(
            assignation=assignation,
            kind=enums.AssignationInstructKind.COLLECT,
            message="Collect",
        )

        AgentConsumer.broadcast(
            assignation.agent.id,
            message=messages.Cancel(
                assignation=assignation.id,
            )
        )
        return assignation

   
    def step(self, info: Info,  input: inputs.StepInputModel) -> models.Assignation:
        assignation = models.Assignation.objects.get(id=input.assignation)
        assignation.status = enums.AssignationStatus.STEP
        assignation.save()

        AgentConsumer.broadcast(
            assignation.agent.id,
            message=messages.Cancel(
                assignation=assignation.id,
            )
        )
        return assignation


controll_backend = RedisControllBackend()
