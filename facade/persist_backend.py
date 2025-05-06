from typing import List
from facade import models, enums, messages
import datetime
import logging


class ModelPersistBackend:
    async def on_agent_disconnected(self, agent_id: str) -> None:
        agent = await models.Agent.objects.aget(id=agent_id)
        agent.connected = False
        agent.last_seen = datetime.datetime.now()
        print(f"Agent {agent} disconnected")

        await agent.asave()

        async for ass in models.Assignation.objects.filter(
            implementation__agent=agent, is_done=False
        ).all():
            await models.AssignationEvent.objects.acreate(
                assignation=ass,
                kind=enums.AssignationEventKind.DISCONNECTED,
                message="Agent disconnected. Fate unknown",
            )
            await ass.asave()

    async def on_agent_connected(self, agent_id: str) -> List[models.Assignation]:
        agent = await models.Agent.objects.aget(id=agent_id)
        agent.connected = True
        agent.last_seen = datetime.datetime.now()
        await agent.asave()

        assignations = []
        async for i in models.Assignation.objects.filter(
            agent=agent, is_done=False
        ).all():
            assignations.append(i)

        return assignations

    async def on_agent_heartbeat(self, agent_id: str) -> None:
        logging.debug(f"On agent Heartbeat {agent_id}")
        x = await models.Agent.objects.aget(id=agent_id)
        x.connected = True
        x.last_seen = datetime.datetime.now()

        await x.asave()

    async def on_agent_log(self, agent_id: str, message: messages.LogEvent) -> None:
        logging.info(f"Log Assignation {message}")

        await models.AssignationEvent.objects.acreate(
            assignation_id=message.assignation,
            kind=enums.AssignationEventKind.LOG,
            message=message.message,
        )

    async def on_agent_yield(self, agent_id: str, message: messages.YieldEvent) -> None:
        logging.info(f"Yield Assignation {message}")

        await models.AssignationEvent.objects.acreate(
            assignation_id=message.assignation,
            kind=enums.AssignationEventKind.YIELD,
            returns=message.returns,
        )

    async def on_agent_done(self, agent_id: str, message: messages.DoneEvent) -> None:
        logging.info(f"Critical Assignation {message}")

        await models.AssignationEvent.objects.acreate(
            assignation_id=message.assignation,
            kind=enums.AssignationEventKind.DONE,
        )

        x = await models.Assignation.objects.aget(id=message.assignation)
        x.is_done = True
        await x.asave()

    async def on_agent_error(self, agent_id: str, message: messages.ErrorEvent) -> None:
        logging.info(f"Critical Assignation {message}")

        await models.AssignationEvent.objects.acreate(
            assignation_id=message.assignation,
            kind=enums.AssignationEventKind.ERROR,
            message=message.error,
        )

        x = await models.Assignation.objects.aget(id=message.assignation)
        x.is_done = True
        await x.asave()

    async def on_agent_critical(
        self, agent_id: str, message: messages.CriticalEvent
    ) -> None:
        logging.info(f"Criticial Assignation {message}")

        await models.AssignationEvent.objects.acreate(
            assignation_id=message.assignation,
            kind=enums.AssignationEventKind.CRITICAL,
            message=message.error,
        )

        x = await models.Assignation.objects.aget(id=message.assignation)
        x.is_done = True
        await x.asave()

    async def on_agent_progress(
        self, agent_id: str, message: messages.ProgressEvent
    ) -> None:
        logging.info(f"Progress Assignation {message}")

        await models.AssignationEvent.objects.acreate(
            assignation_id=message.assignation,
            kind=enums.AssignationEventKind.PROGRESS,
            progress=message.progress,
            message=message.message,
        )


persist_backend = ModelPersistBackend()
