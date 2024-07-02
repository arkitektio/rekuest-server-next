import uuid
from random import choice
from typing import Protocol

from facade import enums, inputs, models, types
from facade.consumers.async_consumer import AgentConsumer
from kante.types import Info


class ControllBackend(Protocol):

    def activate_provision(self, provision: models.Provision) -> None: ...

    def deactivate_provision(self, provision: models.Provision) -> None: ...


# Basic finder


def find_best_fitting_provision(
    node_id: str, user: models.User
) -> models.Provision:
    
    provision = models.Provision.objects.filter(template__node_id=node_id, status=enums.ProvisionStatus.ACTIVE).first()


    return provision

def find_best_fitting_provision(
    node_id: str, user: models.User
) -> models.Provision:
    
    provision = models.Provision.objects.filter(template__node_id=node_id, status=enums.ProvisionStatus.ACTIVE).first()


    return provision


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

    def interrupt(self, input: inputs.InterruptInputModel) -> types.Assignation:
        parent = models.Assignation.objects.get(id=input.assignation)
        children = models.Assignation.objects.filter(parent_id=input.assignation).all()

        assignation = models.Assignation.objects.get(id=input.assignation)
        assignation.status = enums.AssignationStatus.INTERRUPTED
        assignation.save()

        AgentConsumer.broadcast(
            assignation.provision.agent.id,
            {
                "type": "INTERRUPT",
                "assignation": assignation.id,
                "id": self.create_message_id(),
            },
        )
        return assignation
    

    def reserve(self, info: Info, input: inputs.ReserveInputModel) -> types.Reservation:

        if input.node is None and input.template is None:
            raise ValueError("Either node or template must be provided")
        



        node = models.Node.objects.get(id=input.node) if input.node else None
        template = models.Template.objects.get(id=input.template) if input.template else None


        node_id = node.id if node else template.node.id


        provision = find_best_fitting_provision(node_id, info.context.request.user)
        if not provision:
            raise ValueError("No Assignable Provisions found")

        reference = input.reference or self.create_message_id()

        registry, _ = models.Registry.objects.get_or_create(
            app=info.context.request.app, user=info.context.request.user
        )

        waiter, _ = models.Waiter.objects.get_or_create(
            registry=registry, instance_id=input.instance_id, defaults=dict(name="default")
        )



        res, created = models.Reservation.objects.update_or_create(
            reference=reference,
            node=node or template.node,
            template=template,
            strategy=(
                enums.ReservationStrategy.DIRECT
                if template
                else enums.ReservationStrategy.ROUND_ROBIN
            ),
            waiter=waiter,
            defaults=dict(
                title=input.title,
                binds=input.binds.dict() if input.binds else None,
            ),
            causing_assignation_id=input.assignation_id,
        )

        # TODO: Find really the best fitting provision

        res.provisions.set([provision])




        # TODO: Cache the reservation in the redis cache and make it available for the assignation



        return res


    def cancel(self, input: inputs.CancelInputModel) -> types.Assignation:
        assignation = models.Assignation.objects.get(id=input.assignation)
        assignation.status = enums.AssignationStatus.CANCELLED
        assignation.save()

        AgentConsumer.broadcast(
            assignation.provision.agent.id,
            {
                "type": "CANCEL",
                "assignation": assignation.id,
                "id": self.create_message_id(),
                "provision": assignation.provision.id,
            },
        )
        return assignation

    def assign(self, info: Info, input: inputs.AssignInputModel) -> types.Assignation:

        # TODO: Check if function is cached and was

        provision = None
        reservation= None
        template = None

        waiter = get_waiter_for_context(info, input.instance_id)




        if input.reservation:

            # TODO: Retrieve the reservation in the redis cache wth the provision keys set
            reservation = models.Reservation.objects.prefetch_related("provisions").get(
                id=input.reservation
            )

            # TODO: Cache the reservation in the redis cache
            provision = choice(reservation.provisions.all())

        elif input.template:

            template = models.Template.objects.get(id=input.template)

             # TODO: Cache the reservation in the redis cache
            provision = template.provision

        elif input.node:

            provision = find_best_fitting_provision(input.node, info.context.request.user)

        else:
            raise ValueError("You need to provide either, node, template, or reservation to created an assignment")

        if not provision:
            raise ValueError("No active provision found")

        reference = input.reference or self.create_message_id()

        

        assignation = models.Assignation.objects.create(
            reservation=reservation,
            args=input.args,
            reference=reference,
            parent_id=input.parent,
            node=provision.template.node,
            provision=provision,
            status="BOUND",
            hooks=input.hooks or [],
            waiter=waiter,
            template=template
        )

        AgentConsumer.broadcast(
            provision.agent.id,
            {
                "type": "ASSIGN",
                "waiter": waiter.id,
                "reservation": reservation.id if reservation else None,
                "provision": provision.id,
                "args": input.args,
                "id": reference,
                "assignation": assignation.id,
            },
        )
        if input.hooks:
            for hook in input.hooks:
                if hook.kind == enums.HookKind.INIT:
                    self.assign(
                        inputs.AssignInputModel(
                            node=hook.hash,
                            args={"assignation": assignation.id},
                            reference="init_hook_0",
                        )
                    )

        return assignation

    def activate_provision(self, provision: models.Provision) -> None:
        AgentConsumer.broadcast(
            provision.agent.id, {"type": "activate", "id": self.create_message_id()}
        )

    def deactivate_provision(self, provision: models.Provision) -> None:
        AgentConsumer.broadcast(
            provision.agent.id,
            {
                "type": "deactivate",
                "provision": provision.id,
                "id": self.create_message_id(),
            },
        )

    def provide(self, provision: models.Provision) -> None:
        AgentConsumer.broadcast(
            provision.agent.id,
            {
                "type": "PROVIDE",
                "provision": provision.id,
                "id": self.create_message_id(),
            },
        )

    def unprovide(self, provision: models.Provision) -> None:
        AgentConsumer.broadcast(
            provision.agent.id,
            {
                "type": "UNPROVIDE",
                "provision": provision.id,
                "id": self.create_message_id(),
            },
        )


controll_backend = RedisControllBackend()
