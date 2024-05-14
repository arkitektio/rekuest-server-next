from typing import Protocol
from facade import models, enums, logic
import uuid



class ModelPersistBackend():



    async def on_provide_changed(self, message: dict) -> None:

        kind_of_change = message["kind"]


        await models.ProvisionEvent.objects.acreate(provision_id=message["provision"], kind=message["kind"], message=message["message"])
        x = await models.Provision.objects.aget(id=message["provision"])


        if kind_of_change == enums.ProvisionEventKind.ACTIVE:
            print("ACTIVE")
            await logic.aset_provision_provided(x)

        if kind_of_change == enums.ProvisionEventKind.DISCONNECTED:
            print("DISCONNECTED")
            await logic.aset_provision_unprovided(x)


        if kind_of_change != "LOG":
            x.status = message["kind"]
            await x.asave()
        print("PROVIDE CHANGED", message)

    async def on_assign_changed(self, message: dict) -> None:
        kind_of_change = message["kind"]

        await models.AssignationEvent.objects.acreate(assignation_id=message["assignation"], kind=message["kind"], message=message["message"], returns=message["returns"])
        x = await models.Assignation.objects.aget(id=message["assignation"])

        if kind_of_change != "LOG":
            x.status = message["kind"]
            await x.asave()
            
        print("Assig  CHANGED", message)


    async def aget_provisions(self, agent: models.Agent) -> list[models.Provision]:
        return await agent.provisions.aall()









persist_backend = ModelPersistBackend()