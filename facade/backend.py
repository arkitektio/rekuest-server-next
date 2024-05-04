from typing import Protocol
from facade import models, enums, inputs, types
from facade.consumers.async_consumer import AgentConsumer
import uuid
from random import choice


class ControllBackend(Protocol):


    def activate_provision(self, provision: models.Provision) -> None:
        ...

    def deactivate_provision(self, provision: models.Provision) -> None:
        ...




class RedisControllBackend(ControllBackend):


    def create_message_id(self) -> str:
        return str(uuid.uuid4())
    

    def interrupt(self, input: inputs.InterruptInputModel) -> types.Assignation:
        parent= models.Assignation.objects.get(id=input.assignation)
        children = models.Assignation.objects.filter(parent_id=input.assignation).all()


        assignation = models.Assignation.objects.get(id=input.assignation)
        assignation.status = enums.AssignationStatus.INTERRUPTED
        assignation.save()

        AgentConsumer.broadcast(assignation.provision.agent.id, {"type": "INTERRUPT", "assignation": assignation.id, "id": self.create_message_id()})
        return assignation


    def cancel(self, input: inputs.CancelInputModel) -> types.Assignation:
        assignation = models.Assignation.objects.get(id=input.assignation)
        assignation.status = enums.AssignationStatus.CANCELLED
        assignation.save()

        AgentConsumer.broadcast(assignation.provision.agent.id, {"type": "CANCEL", "assignation": assignation.id, "id": self.create_message_id(), "provision": assignation.provision.id})
        return assignation

    def assign(self, input: inputs.AssignInputModel) -> types.Assignation:


        reservation = models.Reservation.objects.prefetch_related("provisions").get(id=input.reservation)


        random_provision = choice(reservation.provisions.filter(status=enums.ProvisionStatus.ACTIVE).all())

        if not random_provision:
            raise ValueError("No active provision found")
    

        assignation = models.Assignation.objects.create(reservation_id=input.reservation, args=input.args, reference=input.reference or uuid.uuid4(), parent_id=input.parent, provision=random_provision, status="BOUND")
        AgentConsumer.broadcast(random_provision.agent.id, {"type": "ASSIGN", "reservation": reservation.id, "provision": random_provision.id, "args": input.args, "id": self.create_message_id(), "assignation": assignation.id})

        return assignation

        









    def activate_provision(self, provision: models.Provision) -> None:
        AgentConsumer.broadcast(provision.agent.id, {"type": "activate", "id": self.create_message_id()})

    def deactivate_provision(self, provision: models.Provision) -> None:
        AgentConsumer.broadcast(provision.agent.id, {"type": "deactivate", "provision": provision.id, "id": self.create_message_id()})

    
    def provide(self, provision: models.Provision) -> None:
        AgentConsumer.broadcast(provision.agent.id, {"type": "PROVIDE", "provision": provision.id,"id": self.create_message_id()})


    def unprovide(self, provision: models.Provision) -> None:
        AgentConsumer.broadcast(provision.agent.id, {"type": "UNPROVIDE", "provision": provision.id, "id": self.create_message_id()})









controll_backend = RedisControllBackend()