from typing import Protocol
from facade import models
from facade.consumers.async_consumer import AgentConsumer

class ControllBackend(Protocol):


    def activate_provision(self, provision: models.Provision) -> None:
        ...

    def deactivate_provision(self, provision: models.Provision) -> None:
        ...




class RedisControllBackend(ControllBackend):

    def activate_provision(self, provision: models.Provision) -> None:
        AgentConsumer.broadcast(provision.agent.id, {"type": "activate", "id": provision.id})

    def deactivate_provision(self, provision: models.Provision) -> None:
        AgentConsumer.broadcast(provision.agent.id, {"type": "deactivate", "id": provision.id})








controll_backend = RedisControllBackend()