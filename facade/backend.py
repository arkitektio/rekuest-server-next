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
    return choice(models.Node.objects.get(id=node_id).templates.all()).provision


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
            provision = choice(reservation.provisions)

        else:

            provision = find_best_fitting_provision(input.node, info.context.request.user)

        if not provision:
            raise ValueError("No active provision found")

        reference = input.reference or self.create_message_id()

        

        assignation = models.Assignation.objects.create(
            reservation_id=input.reservation,
            args=input.args,
            reference=reference,
            parent_id=input.parent,
            node=provision.template.node,
            provision=provision,
            status="BOUND",
            hooks=input.hooks,
            waiter=waiter,
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
