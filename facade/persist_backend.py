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

        async for ass in models.Assignation.objects.filter(implementation__agent=agent, is_done=False).all():
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
        async for i in models.Assignation.objects.filter(agent=agent, is_done=False).all():
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
        x.finished_at = datetime.datetime.now()
        x.latest_event_kind = enums.AssignationEventKind.DONE
        await x.asave()

    async def on_agent_cancelled(self, agent_id: str, message: messages.CancelledEvent) -> None:
        logging.info(f"Critical Assignation {message}")

        await models.AssignationEvent.objects.acreate(
            assignation_id=message.assignation,
            kind=enums.AssignationEventKind.CANCELLED,
        )

        x = await models.Assignation.objects.aget(id=message.assignation)
        x.is_done = True
        x.finished_at = datetime.datetime.now()
        x.latest_event_kind = enums.AssignationEventKind.CANCELLED
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
        x.finished_at = datetime.datetime.now()
        x.latest_event_kind = enums.AssignationEventKind.ERROR
        await x.asave()

    async def on_agent_critical(self, agent_id: str, message: messages.CriticalEvent) -> None:
        logging.info(f"Criticial Assignation {message}")

        await models.AssignationEvent.objects.acreate(
            assignation_id=message.assignation,
            kind=enums.AssignationEventKind.CRITICAL,
            message=message.error,
        )

        x = await models.Assignation.objects.aget(id=message.assignation)
        x.is_done = True
        x.finished_at = datetime.datetime.now()
        x.latest_event_kind = enums.AssignationEventKind.CRITICAL
        await x.asave()

    async def on_agent_progress(self, agent_id: str, message: messages.ProgressEvent) -> None:
        logging.info(f"Progress Assignation {message}")

        await models.AssignationEvent.objects.acreate(
            assignation_id=message.assignation,
            kind=enums.AssignationEventKind.PROGRESS,
            progress=message.progress,
            message=message.message,
        )

    async def on_agent_state_patch(self, agent_id: str, message: messages.StatePatchEvent) -> None:
        logging.info(f"Log Patch for Assignation {message.state_name}")

        state = await models.State.objects.aget(agent_id=agent_id, interface=message.state_name)
        session, _ = await models.Session.objects.aget_or_create(agent_id=agent_id, session_id=message.session_id)

        await models.Patch.objects.acreate(
            state=state,
            agent_id=agent_id,
            session=session,
            interface=message.state_name,
            op=message.op,
            path=message.path,
            value=message.value,
            assignation_id=message.correlation_id,
            global_rev=message.global_rev,
        )

    async def on_agent_state_snapshot(self, agent_id: str, message: messages.StateSnapshotEvent) -> None:
        logging.info(f"Log Snapshot for Assignation {agent_id}")

        session, _ = await models.Session.objects.aget_or_create(agent_id=agent_id, session_id=message.session_id)

        for state_name, snapshot in message.snapshots.items():
            state = await models.State.objects.aget(agent_id=agent_id, interface=state_name)
            agent = await models.Agent.objects.aget(id=agent_id)

            await models.Snapshot.objects.acreate(
                session=session,
                state=state,
                agent=agent,
                value=snapshot,
                global_rev=message.global_rev,
            )

    async def on_agent_session_init(self, agent_id: str, message: messages.SessionInitMessage) -> None:
        logging.info(f"Session init {message.session_id} with data {message}")
        # For now we don't do anything with this, but it could be used to initialize session-specific data

        session, _ = await models.Session.objects.aget_or_create(agent_id=agent_id, session_id=message.session_id)

        for state_name, snapshot in message.states.items():
            state = await models.State.objects.aget(agent_id=agent_id, interface=state_name)
            agent = await models.Agent.objects.aget(id=agent_id)

            await models.Snapshot.objects.acreate(
                session=session,
                state=state,
                agent=agent,
                value=snapshot,
                global_rev=0,
            )


persist_backend = ModelPersistBackend()
