from typing import Protocol
from facade import models, enums, logic
import uuid
import datetime
from django.conf import settings
from asgiref.sync import async_to_sync

class ModelPersistBackend():







    async def on_reinit(self, agent_id: str | None) -> None:
        if agent_id:
            agent = models.Agent.objects.aget(id=agent_id)

            if agent.last_seen < datetime.datetime.now() - datetime.timedelta(seconds=settings.AGENT_DISCONNECTED_TIMEOUT):
                await self.on_agent_disconnected(agent_id)

        else:
            agents = models.Agent.objects.filter(last_seen__lt=datetime.datetime.now() - datetime.timedelta(seconds=settings.AGENT_DISCONNECTED_TIMEOUT)).all()
            async for agent in agents:
               await self.on_agent_disconnected(agent.id)

    async def on_agent_connected(self, agent_id: str) -> None:
        x = await models.Agent.objects.aget(id=agent_id)
        x.status = enums.AgentStatus.ACTIVE
        x.connected = True
        x.last_seen = datetime.datetime.now()
        await x.asave()

    async def on_agent_disconnected(self, agent_id: str) -> None:
        agent = await models.Agent.objects.aget(id=agent_id)
        agent.status = enums.AgentStatus.DISCONNECTED
        agent.connected = False
        agent.last_seen = datetime.datetime.now()

        async for i in models.Provision.objects.filter(agent=agent).all():
            created = await models.ProvisionEvent.objects.acreate(provision=i, kind=enums.ProvisionEventKind.DISCONNECTED, message="Agent disconnected")
            i.status = enums.ProvisionEventKind.DISCONNECTED
            i.provided = False
            
            await logic.aset_provision_unprovided(i)

            async for ass in models.Assignation.objects.filter(provision=i).exclude(status__in=[enums.AssignationEventKind.CANCELLED, enums.AssignationEventKind.DONE, enums.AssignationEventKind.CRITICAL]).all():
                created = await models.AssignationEvent.objects.acreate(assignation=ass, kind=enums.AssignationEventKind.DISCONNECTED, message="Agent disconnected. Fate unknown")
                ass.status = enums.AssignationEventKind.DISCONNECTED
                print("Deactivating Assignation", ass.id)
                await ass.asave()


            await i.asave()






        await agent.asave()


    async def on_agent_heartbeat(self, agent_id: str) -> None:
        print("On agent Heartbeat")
        x = await models.Agent.objects.aget(id=agent_id)
        x.status = enums.AgentStatus.ACTIVE
        x.connected = True
        x.last_seen = datetime.datetime.now()

        await x.asave()



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

        await models.AssignationEvent.objects.acreate(assignation_id=message["assignation"], kind=message["kind"], message=message["message"], returns=message["returns"], progress=message.get("progress", None))
       

        if kind_of_change == "DONE" or kind_of_change == "CANCELLED" or kind_of_change == "CRITICAL" or kind_of_change == "DISCONNECTED":
            x = await models.Assignation.objects.aget(id=message["assignation"])
            x.status = kind_of_change
            await x.asave()
            print("Changed Assignation")
            
        print("Assig  CHANGED", message)


    async def aget_provisions(self, agent: models.Agent) -> list[models.Provision]:
        return await agent.provisions.aall()









persist_backend = ModelPersistBackend()