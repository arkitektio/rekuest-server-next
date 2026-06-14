from typing import List, Optional
from facade import models, enums, messages
from facade.higher_order import project_returns
from django.utils import timezone
import logging

_TERMINAL_KINDS = (
    enums.AssignationEventKind.DONE,
    enums.AssignationEventKind.CANCELLED,
    enums.AssignationEventKind.ERROR,
    enums.AssignationEventKind.CRITICAL,
)


class ModelPersistBackend:
    async def _unfold_to_higher_order(self, child_assignation_id: str, kind, returns: Optional[dict] = None, message: Optional[str] = None) -> None:
        """If this assignation is the child of a higher-order wrapper, re-emit a mapped event on it.

        The lower implementation runs on a child assignation; the user watches the wrapper. So we
        project the child's returns back onto the wrapper's return ports and emit the corresponding
        event on the wrapper (linked via ``delegated_to``), which the subscription layer broadcasts.
        Non-higher-order children (hooks, dependency sub-assignments) are ignored.
        """
        try:
            child = await models.Assignation.objects.select_related("parent", "parent__implementation").aget(id=child_assignation_id)
        except models.Assignation.DoesNotExist:
            return

        parent = child.parent
        if parent is None:
            return
        parent_impl = parent.implementation
        if parent_impl is None or parent_impl.higher_order_for_id is None:
            return  # not a higher-order child

        config = parent_impl.higher_order_config or {}

        event_kwargs = dict(assignation=parent, kind=kind, delegated_to=child)
        if kind == enums.AssignationEventKind.YIELD:
            event_kwargs["returns"] = project_returns(config, returns)
        if message is not None:
            event_kwargs["message"] = message
        await models.AssignationEvent.objects.acreate(**event_kwargs)

        parent.latest_event_kind = kind
        update_fields = ["latest_event_kind"]
        if kind in _TERMINAL_KINDS:
            parent.is_done = True
            parent.finished_at = timezone.now()
            update_fields += ["is_done", "finished_at"]
        await parent.asave(update_fields=update_fields)

    async def on_agent_disconnected(self, agent_id: str, connection_id: str | None = None) -> None:
        agent = await models.Agent.objects.aget(id=agent_id)

        # Generation guard: if a newer connection has already taken over this
        # agent (``active_connection_id`` no longer points at us), this is a
        # displaced connection shutting down. Do NOT flip ``connected`` off or
        # mark assignations disconnected — the new owner is authoritative.
        if connection_id is not None and agent.active_connection_id != connection_id:
            return

        agent.connected = False
        agent.last_seen = timezone.now()
        await agent.asave(update_fields=["connected", "last_seen"])

        # Same predicate as ``on_agent_connected`` (direct ``agent`` FK): an
        # assignation may have a null/reassigned implementation, so filtering by
        # ``implementation__agent`` would silently skip work this agent owns.
        async for ass in models.Assignation.objects.filter(agent_id=agent_id, is_done=False).all():
            await models.AssignationEvent.objects.acreate(
                assignation=ass,
                kind=enums.AssignationEventKind.DISCONNECTED,
                message="Agent disconnected. Fate unknown",
            )
            ass.latest_event_kind = enums.AssignationEventKind.DISCONNECTED
            await ass.asave(update_fields=["latest_event_kind"])

    async def on_agent_connected(self, agent_id: str, connection_id: str | None = None) -> List[models.Assignation]:
        agent = await models.Agent.objects.aget(id=agent_id)
        agent.connected = True
        agent.last_seen = timezone.now()
        agent.active_connection_id = connection_id
        await agent.asave(update_fields=["connected", "last_seen", "active_connection_id"])

        assignations = []
        async for i in models.Assignation.objects.filter(agent=agent, is_done=False).all():
            assignations.append(i)

        return assignations

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
        await self._unfold_to_higher_order(message.assignation, enums.AssignationEventKind.YIELD, returns=message.returns)

    async def on_agent_done(self, agent_id: str, message: messages.DoneEvent) -> None:
        logging.info(f"Critical Assignation {message}")

        await models.AssignationEvent.objects.acreate(
            assignation_id=message.assignation,
            kind=enums.AssignationEventKind.DONE,
        )

        x = await models.Assignation.objects.aget(id=message.assignation)
        x.is_done = True
        x.finished_at = timezone.now()
        x.latest_event_kind = enums.AssignationEventKind.DONE
        await x.asave(update_fields=["is_done", "finished_at", "latest_event_kind"])
        await self._unfold_to_higher_order(message.assignation, enums.AssignationEventKind.DONE)

    async def on_agent_cancelled(self, agent_id: str, message: messages.CancelledEvent) -> None:
        logging.info(f"Critical Assignation {message}")

        await models.AssignationEvent.objects.acreate(
            assignation_id=message.assignation,
            kind=enums.AssignationEventKind.CANCELLED,
        )

        x = await models.Assignation.objects.aget(id=message.assignation)
        x.is_done = True
        x.finished_at = timezone.now()
        x.latest_event_kind = enums.AssignationEventKind.CANCELLED
        await x.asave(update_fields=["is_done", "finished_at", "latest_event_kind"])
        await self._unfold_to_higher_order(message.assignation, enums.AssignationEventKind.CANCELLED)

    async def on_agent_error(self, agent_id: str, message: messages.ErrorEvent) -> None:
        logging.info(f"Critical Assignation {message}")

        await models.AssignationEvent.objects.acreate(
            assignation_id=message.assignation,
            kind=enums.AssignationEventKind.ERROR,
            message=message.error,
        )

        x = await models.Assignation.objects.aget(id=message.assignation)
        x.is_done = True
        x.finished_at = timezone.now()
        x.latest_event_kind = enums.AssignationEventKind.ERROR
        await x.asave(update_fields=["is_done", "finished_at", "latest_event_kind"])
        await self._unfold_to_higher_order(message.assignation, enums.AssignationEventKind.ERROR, message=message.error)

    async def on_agent_critical(self, agent_id: str, message: messages.CriticalEvent) -> None:
        logging.info(f"Criticial Assignation {message}")

        await models.AssignationEvent.objects.acreate(
            assignation_id=message.assignation,
            kind=enums.AssignationEventKind.CRITICAL,
            message=message.error,
        )

        x = await models.Assignation.objects.aget(id=message.assignation)
        x.is_done = True
        x.finished_at = timezone.now()
        x.latest_event_kind = enums.AssignationEventKind.CRITICAL
        await x.asave(update_fields=["is_done", "finished_at", "latest_event_kind"])
        await self._unfold_to_higher_order(message.assignation, enums.AssignationEventKind.CRITICAL, message=message.error)

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
        agent = await models.Agent.objects.aget(id=agent_id)

        for state_name, snapshot in message.snapshots.items():
            state = await models.State.objects.aget(agent_id=agent_id, interface=state_name)

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
        agent = await models.Agent.objects.aget(id=agent_id)

        for state_name, snapshot in message.states.items():
            state = await models.State.objects.aget(agent_id=agent_id, interface=state_name)

            await models.Snapshot.objects.acreate(
                session=session,
                state=state,
                agent=agent,
                value=snapshot,
                global_rev=0,
            )


persist_backend = ModelPersistBackend()
