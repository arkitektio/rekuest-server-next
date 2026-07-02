import logging
from typing import List, Optional, Tuple

from asgiref.sync import sync_to_async
from channels.db import database_sync_to_async
from django.utils import timezone

from facade import inputs, models, enums, messages
from facade.grace import GraceScheduler, grace_seconds, progress_lease_seconds
from facade.higher_order import project_returns
from facade.messages import AgentMode

_TERMINAL_KINDS = (
    enums.TaskEventKind.COMPLETED,
    enums.TaskEventKind.CANCELLED,
    enums.TaskEventKind.INTERRUPTED,
    enums.TaskEventKind.FAILED,
    enums.TaskEventKind.CRITICAL,
)


class ModelPersistBackend:
    """The DB-truth backend (satisfies :class:`facade.ports.PersistBackend`).

    The reconcile logic is a set of pure, idempotent DB operations (``reconcile_*``); the
    in-memory :class:`~facade.grace.GraceScheduler` timers are just one *responsive* trigger
    over them (a reconnect or the periodic sweep are interchangeable triggers).
    """

    def __init__(self) -> None:
        # Responsive reconcile triggers (in-memory; the DB is authoritative). Keyed:
        # ``_executor_grace`` by agent id (executor death → fail its executed work);
        # ``_caller_grace`` by caller session id / connection id (caller death → cancel
        # originated roots); ``_progress_leases`` by task id (silent physical op).
        self._executor_grace = GraceScheduler()
        self._caller_grace = GraceScheduler()
        self._progress_leases = GraceScheduler()
        # auto_interrupt escalation timers (keyed by task id): a cancel with an
        # auto_interrupt window escalates to an interrupt if not confirmed in time.
        self._auto_interrupt = GraceScheduler()

    async def _unfold_to_higher_order(self, child_task_id: str, kind, returns: Optional[dict] = None, message: Optional[str] = None) -> None:
        """If this task is the child of a higher-order wrapper, re-emit a mapped event on it.

        The lower implementation runs on a child task; the user watches the wrapper. So we
        project the child's returns back onto the wrapper's return ports and emit the corresponding
        event on the wrapper (linked via ``delegated_to``), which the subscription layer broadcasts.
        Non-higher-order children (hooks, dependency sub-assignments) are ignored.
        """
        try:
            child = await models.Task.objects.select_related("parent", "parent__implementation").aget(id=child_task_id)
        except models.Task.DoesNotExist:
            return

        parent = child.parent
        if parent is None:
            return
        parent_impl = parent.implementation
        if parent_impl is None or parent_impl.higher_order_for_id is None:
            return  # not a higher-order child

        config = parent_impl.higher_order_config or {}

        event_kwargs = dict(task=parent, kind=kind, delegated_to=child)
        if kind == enums.TaskEventKind.YIELD:
            event_kwargs["returns"] = project_returns(config, returns)
        if message is not None:
            event_kwargs["message"] = message
        await models.TaskEvent.objects.acreate(**event_kwargs)

        parent.latest_event_kind = kind
        update_fields = ["latest_event_kind"]
        if kind in _TERMINAL_KINDS:
            parent.is_done = True
            parent.finished_at = timezone.now()
            update_fields += ["is_done", "finished_at"]
        await parent.asave(update_fields=update_fields)

    async def on_agent_disconnected(self, agent_id: int, connection_id: str | None = None) -> None:
        agent = await models.Agent.objects.aget(id=agent_id)

        # Generation guard: if a newer connection has already taken over this
        # agent (``active_connection_id`` no longer points at us), this is a
        # displaced connection shutting down. Do NOT flip ``connected`` off or
        # cascade — the new owner is authoritative.
        if connection_id is not None and agent.active_connection_id != connection_id:
            return

        agent.connected = False
        agent.last_seen = timezone.now()
        await agent.asave(update_fields=["connected", "last_seen"])

        # Grace window: instead of failing in-flight work immediately, wait — a brief blip
        # that reconnects with the same session reclaims it (on_agent_connected cancels the
        # timer). grace<=0 keeps the legacy immediate, inline behaviour (deterministic).
        grace = grace_seconds(AgentMode.EXECUTOR)
        if grace <= 0:
            await self.reconcile_orphaned_executor_work(agent_id)
            return

        self._executor_grace.schedule(agent_id, grace, lambda: self.reconcile_orphaned_executor_work(agent_id))

    async def reconcile_orphaned_executor_work(self, agent_id: int) -> None:
        """Fail an executor's in-flight work after a confirmed loss. Pure, idempotent DB op.

        The authoritative reconcile shared by all three triggers (grace timer, reconnect with
        a fresh session, and the periodic sweep). No-op if the agent reconnected in the
        meantime (``connected`` is back True).
        """
        agent = await models.Agent.objects.aget(id=agent_id)
        if agent.connected:
            return
        in_flight = [a async for a in models.Task.objects.select_related("implementation", "action").filter(agent_id=agent_id, is_done=False)]
        await self._fail_and_cascade_inflight(in_flight)

    def _build_redispatch_assign_sync(self, task_id: int) -> "messages.Assign | None":
        """Rebuild the Assign message for an idempotent task's re-dispatch, or None.

        Sync (run via ``database_sync_to_async``): token minting walks lazy FK chains.
        Returns None when the task lacks the identity needed to re-mint (no caller/
        implementation) or when a strict provenance policy refuses — the caller then falls
        back to the DISCONNECTED fate-unknown path.
        """
        from facade.caller_context import CallerContext
        from facade.provenance import mint_token_for_task

        task = models.Task.objects.select_related(
            "agent", "implementation", "action", "caller__user", "caller__client", "caller__organization"
        ).get(pk=task_id)

        if task.implementation is None or task.caller is None or task.caller.user is None or task.caller.organization is None:
            return None

        ctx = CallerContext(user=task.caller.user, client=task.caller.client, organization=task.caller.organization, roles=[])
        try:
            token = mint_token_for_task(task, ctx)
        except ValueError:
            return None

        return messages.Assign(
            task=str(task.pk),
            args=task.args or {},
            user=str(task.caller.user.sub),
            org=str(task.caller.organization.slug),
            reference=str(task.reference) if task.reference is not None else None,
            capture=task.capture,
            resolution=str(task.resolution_id) if task.resolution_id else None,
            interface=task.implementation.interface,
            action=str(task.action.hash),
            implementation=str(task.implementation_id),
            parent=str(task.parent_id) if task.parent_id else None,
            root=str(task.root_id) if task.root_id else None,
            token=token,
        )

    async def _fail_and_cascade_inflight(self, tasks: List[models.Task]) -> None:
        """Mark orphaned in-flight work along the retry axis.

        ``effect:physical`` failed ambiguously (the executor vanished) → CRITICAL (terminal,
        never retried). Idempotent actions → QUEUED + the Assign re-broadcast into the
        agent's redis queue (which retains messages for offline agents), so the work re-runs
        on reconnect — a same-session reclaim after grace expiry may double-execute, which is
        safe by the idempotent contract. Everything else → DISCONNECTED (fate unknown,
        recoverable but never automatically resolved).
        """
        from facade.consumers.async_consumer import AgentConsumer  # lazy: avoids import cycle

        for task in tasks:
            self._auto_interrupt.cancel(task.pk)
            implementation = task.implementation
            effect = implementation.effect if implementation is not None else enums.EffectClassChoices.NONE.value
            if effect == enums.EffectClassChoices.PHYSICAL.value:
                await models.TaskEvent.objects.acreate(
                    task=task,
                    kind=enums.TaskEventKind.CRITICAL,
                    message="Executor lost while running physical-effect work — terminal, not retried.",
                )
                task.is_done = True
                task.finished_at = timezone.now()
                task.latest_event_kind = enums.TaskEventKind.CRITICAL
                await task.asave(update_fields=["latest_event_kind", "is_done", "finished_at"])
                continue

            # The ``!= QUEUED`` guard makes the periodic sweep re-entrant: reconciling an
            # already-requeued task again must not pile duplicate Assigns into the queue.
            if task.action is not None and task.action.idempotent and task.latest_event_kind != enums.TaskEventKind.QUEUED:
                assign_message = await database_sync_to_async(self._build_redispatch_assign_sync)(task.pk)
                if assign_message is not None:
                    await models.TaskEvent.objects.acreate(
                        task=task,
                        kind=enums.TaskEventKind.QUEUED,
                        message="Executor lost — idempotent action re-queued for redelivery.",
                    )
                    task.latest_event_kind = enums.TaskEventKind.QUEUED
                    await task.asave(update_fields=["latest_event_kind"])
                    await sync_to_async(AgentConsumer.broadcast)(task.agent_id, assign_message)
                    continue
                # No re-dispatchable identity → fall through to fate-unknown.

            await models.TaskEvent.objects.acreate(
                task=task,
                kind=enums.TaskEventKind.DISCONNECTED,
                message="Agent disconnected. Fate unknown",
            )
            task.latest_event_kind = enums.TaskEventKind.DISCONNECTED
            await task.asave(update_fields=["latest_event_kind"])

    async def on_agent_connected(self, agent_id: int, connection_id: str | None = None, session_id: str | None = None) -> List[models.Task]:
        agent = await models.Agent.objects.aget(id=agent_id)
        prior_session = agent.active_session_id

        # We are deciding reclaim-vs-cascade now, so cancel any pending grace timer.
        self._executor_grace.cancel(agent_id)

        agent.connected = True
        agent.last_seen = timezone.now()
        agent.active_connection_id = connection_id
        agent.active_session_id = session_id
        await agent.asave(update_fields=["connected", "last_seen", "active_connection_id", "active_session_id"])

        in_flight = [a async for a in models.Task.objects.select_related("implementation", "action").filter(agent_id=agent_id, is_done=False)]

        # A different session means a FRESH process took over (the old one died): the prior
        # in-flight work is orphaned and must fail-and-cascade rather than be reclaimed.
        if prior_session is not None and session_id is not None and prior_session != session_id:
            await self._fail_and_cascade_inflight(in_flight)
            return []

        # Same session (or first connect / no session info) → reclaim: hand the in-flight
        # work back as inquiries so the surviving process can re-sync.
        return in_flight

    async def get_or_create_caller_id(self, agent_id: int) -> str:
        """The durable ``Caller`` id for an agent's identity (user/client/organization).

        A connection joins ``task_caller_{caller_id}`` to receive the events of work it
        originated. Mirrors ``get_caller_for_context`` (``facade/backend.py``) but resolves
        the identity from the agent instead of a GraphQL request.
        """
        agent = await models.Agent.objects.select_related("user", "client", "organization").aget(id=agent_id)
        caller, _ = await models.Caller.objects.aget_or_create(
            client=agent.client,
            user=agent.user,
            organization=agent.organization,
        )
        return str(caller.pk)

    async def on_caller_assign(
        self,
        agent_id: int,
        message: messages.AssignRequest,
        can_assign_root: bool,
        connection_id: str | None = None,
        session_id: str | None = None,
    ) -> Tuple[models.Task, bool]:
        """Originate (or resolve) a task requested by a caller over the socket.

        Idempotent on ``(caller, reference)`` and durable-before-return: a resend of the same
        ``reference`` returns the existing task with ``created=False`` rather than
        creating a duplicate. Raises ``PermissionError`` for a root task when the
        caller lacks ``can_assign_root``. ``connection_id``/``session_id`` are recorded on a
        new *root* task so the caller-death cascade can find it. Runs the sync postman
        backend off the event loop.
        """
        return await database_sync_to_async(self._caller_assign_sync)(agent_id, message, can_assign_root, connection_id, session_id)

    def _caller_assign_sync(
        self,
        agent_id: int,
        message: messages.AssignRequest,
        can_assign_root: bool,
        connection_id: str | None = None,
        session_id: str | None = None,
    ) -> Tuple[models.Task, bool]:
        # Imported lazily: facade.backend → async_consumer → agent_protocol → persist_backend
        # would otherwise be a circular import at module load.
        from facade.backend import controll_backend
        from facade.caller_context import CallerContext
        from facade.provenance import principal

        agent = models.Agent.objects.select_related("user", "client", "organization").get(id=agent_id)
        caller, _ = models.Caller.objects.get_or_create(client=agent.client, user=agent.user, organization=agent.organization)

        # Idempotency: a resend of the same reference returns the existing task.
        existing = models.Task.objects.filter(caller=caller, reference=message.reference).first()
        if existing is not None:
            return existing, False

        is_root = message.parent is None
        if is_root and not can_assign_root:
            raise PermissionError("Not authorized to originate a root task (missing can_assign_root).")

        ctx = CallerContext.from_agent(agent, roles=principal.roles_for_caller(caller))
        hooks = [inputs.HookInputModel(**h) for h in message.hooks] if message.hooks else None
        assign_input = inputs.AssignInputModel(
            reference=message.reference,
            args=message.args,
            action=message.action,
            action_hash=message.action_hash,
            implementation=message.implementation,
            agent=message.agent,
            interface=message.interface,
            parent=message.parent,
            dependency=message.dependency,
            method=message.method,
            resolution=message.resolution,
            hooks=hooks,
            capture=message.capture,
            ephemeral=message.ephemeral,
            step=message.step,
        )
        task = controll_backend.assign(ctx, assign_input)

        # Record origination on a root so the caller-death cascade can find work this live
        # connection/session owns (a dependent task's fate follows its parent).
        if is_root and (connection_id is not None or session_id is not None):
            task.originating_connection_id = connection_id
            task.originating_session_id = session_id
            task.save(update_fields=["originating_connection_id", "originating_session_id"])

        return task, True

    async def on_observer_connected(self, agent_id: int, connection_id: str | None = None, mode: str | None = None) -> List[models.Task]:
        """A non-executor (frontend/caller/observer) connected.

        Non-authoritative: it does NOT flip ``connected`` or claim ``active_connection_id``
        (which belong to the executor singleton — and the row may be shared, per the
        shared-Agent-row decision), and it reconciles no in-flight executor work. Caller
        reclaim of originated roots is handled separately in :meth:`on_caller_connected`.
        """
        return []

    # ----------------------------------------------------------------------- #
    # Caller lifecycle controls (two-phase; the request phase wraps the sync postman backend)
    # ----------------------------------------------------------------------- #
    def _caller_control_sync(self, agent_id: int, task_id: str, op: str, *, step: bool = False) -> models.Task:
        """Ownership-check then dispatch a control op on the sync postman backend.

        A caller may only control tasks whose ``caller`` is its own identity. Raises
        ``Task.DoesNotExist`` (unknown), ``PermissionError`` (not the caller), or
        ``ValueError`` (already terminal — from the postman backend).
        """
        from facade import inputs
        from facade.backend import controll_backend

        agent = models.Agent.objects.select_related("user", "client", "organization").get(id=agent_id)
        caller, _ = models.Caller.objects.get_or_create(client=agent.client, user=agent.user, organization=agent.organization)
        task = models.Task.objects.get(id=task_id)
        if task.caller_id != caller.pk:
            raise PermissionError("Not authorized to control this task (not its caller).")

        ref = str(task_id)
        ops = {
            "cancel": lambda: controll_backend.cancel(inputs.CancelInputModel(task=ref)),
            "interrupt": lambda: controll_backend.interrupt(inputs.InterruptInputModel(task=ref)),
            "pause": lambda: controll_backend.pause(inputs.PauseInputModel(task=ref)),
            "resume": lambda: controll_backend.resume(inputs.ResumeInputModel(task=ref, step=step)),
        }
        return ops[op]()

    async def on_caller_cancel(self, agent_id: int, message: messages.CancelRequest, *, connection_id: str | None = None, session_id: str | None = None) -> models.Task:
        task = await database_sync_to_async(self._caller_control_sync)(agent_id, message.task, "cancel")
        if message.auto_interrupt is not None:
            self._auto_interrupt.schedule(message.task, float(message.auto_interrupt), lambda: self._escalate_to_interrupt(message.task))
        return task

    async def on_caller_interrupt(self, agent_id: int, message: messages.InterruptRequest, *, connection_id: str | None = None, session_id: str | None = None) -> models.Task:
        return await database_sync_to_async(self._caller_control_sync)(agent_id, message.task, "interrupt")

    async def on_caller_pause(self, agent_id: int, message: messages.PauseRequest, *, connection_id: str | None = None, session_id: str | None = None) -> models.Task:
        return await database_sync_to_async(self._caller_control_sync)(agent_id, message.task, "pause")

    async def on_caller_resume(self, agent_id: int, message: messages.ResumeRequest, *, connection_id: str | None = None, session_id: str | None = None) -> models.Task:
        return await database_sync_to_async(self._caller_control_sync)(agent_id, message.task, "resume", step=message.step)

    async def _escalate_to_interrupt(self, task_id: str) -> None:
        """auto_interrupt fired: escalate an unconfirmed cancel to an interrupt. Idempotent."""
        from facade import inputs
        from facade.backend import controll_backend

        def _do() -> None:
            task = models.Task.objects.get(id=task_id)
            if task.is_done:
                return  # the cancel confirmed (or otherwise terminal) before the window — no-op
            controll_backend.interrupt(inputs.InterruptInputModel(task=str(task_id)))

        try:
            await database_sync_to_async(_do)()
        except models.Task.DoesNotExist:
            return

    # ----------------------------------------------------------------------- #
    # Lifecycle confirmation handlers (the second phase)
    # ----------------------------------------------------------------------- #
    async def on_agent_interrupted(self, agent_id: int, message: messages.Interrupted) -> None:
        self._progress_leases.cancel(message.task)
        self._auto_interrupt.cancel(message.task)
        try:
            x = await models.Task.objects.aget(id=message.task)
        except models.Task.DoesNotExist:
            return
        if x.is_done:
            return
        await models.TaskEvent.objects.acreate(task_id=message.task, kind=enums.TaskEventKind.INTERRUPTED)
        x.is_done = True
        x.finished_at = timezone.now()
        x.latest_event_kind = enums.TaskEventKind.INTERRUPTED
        await x.asave(update_fields=["is_done", "finished_at", "latest_event_kind"])
        await self._unfold_to_higher_order(message.task, enums.TaskEventKind.INTERRUPTED)

    async def _on_nonterminal_confirm(self, task_id: str, kind, *, cancel_lease: bool = False) -> None:
        """Persist a non-terminal lifecycle confirmation (paused/resumed)."""
        if cancel_lease:
            self._progress_leases.cancel(task_id)
        try:
            x = await models.Task.objects.aget(id=task_id)
        except models.Task.DoesNotExist:
            return  # a confirmation for an unknown task must not tear down the transport
        if x.is_done:
            return
        await models.TaskEvent.objects.acreate(task_id=task_id, kind=kind)
        x.latest_event_kind = kind
        await x.asave(update_fields=["latest_event_kind"])

    async def on_agent_paused(self, agent_id: int, message: messages.Paused) -> None:
        # A suspended op stops reporting progress — don't let the silent-physical-op lease reap it.
        await self._on_nonterminal_confirm(message.task, enums.TaskEventKind.PAUSED, cancel_lease=True)

    async def on_agent_resumed(self, agent_id: int, message: messages.Resumed) -> None:
        await self._on_nonterminal_confirm(message.task, enums.TaskEventKind.RESUMED)

    async def on_agent_started(self, agent_id: int, message: messages.Started) -> None:
        # The agent accepted and began executing — record it (mirrored to the caller as StartedEvent).
        await self._on_nonterminal_confirm(message.task, enums.TaskEventKind.STARTED)

    async def on_caller_connected(self, agent_id: int, connection_id: str | None = None, session_id: str | None = None) -> None:
        """A participant that may originate work connected — reclaim its orphaned roots.

        Called for EVERY mode (any can originate work; executors assign dependents,
        orchestrators/callers assign roots). Cancels a pending caller-death grace timer for
        this session (the process survived) and re-points the roots it originated to the new
        connection so a later disconnect of *this* connection owns them. Sessionless callers
        cannot be reclaimed (their death is final after grace).
        """
        self._caller_grace.cancel(session_id or connection_id)
        if session_id is not None and connection_id is not None:
            await models.Task.objects.filter(originating_session_id=session_id, is_done=False).aupdate(originating_connection_id=connection_id)

    async def on_caller_disconnected(self, agent_id: int, connection_id: str | None = None, session_id: str | None = None, mode: str | None = None) -> None:
        """A participant that may originate work disconnected — cascade-cancel its roots.

        Observers originate nothing, so they are a no-op. Otherwise, after the per-mode grace
        window (so a quick reconnect with the same session can reclaim via
        :meth:`on_caller_connected`), every still-running task this connection
        originated is cancelled down to its executing agents. grace<=0 cancels inline.
        """
        if mode == AgentMode.OBSERVER.value:
            return

        grace = grace_seconds(mode)
        if grace <= 0:
            await self.reconcile_caller_roots(connection_id, session_id)
            return

        key = session_id or connection_id
        if key is not None:
            self._caller_grace.schedule(key, grace, lambda: self.reconcile_caller_roots(connection_id, session_id))

    async def reconcile_caller_roots(self, connection_id: Optional[str], session_id: Optional[str] = None) -> None:
        """Cancel every still-running root a (dead) connection originated. Pure, idempotent DB op.

        Reclaim guard is implicit: ``on_caller_connected`` re-points reclaimed roots to the
        new connection, so a filter by the OLD ``connection_id`` finds only genuinely-orphaned
        work. Cancellation is a deliberate stop (a nice ``Cancel`` to each executor), so it
        applies regardless of effect class — the effect rule governs ambiguous failure, not
        an intentional cancel.
        """
        if connection_id is None:
            return
        async for root in models.Task.objects.filter(originating_connection_id=connection_id, is_done=False):
            await self._cancel_task_tree(root)

    async def _cancel_task_tree(self, root: models.Task) -> None:
        from facade.consumers.async_consumer import AgentConsumer  # lazy: avoids import cycle

        stack = [root]
        while stack:
            task = stack.pop()
            if task.is_done:
                continue
            self._auto_interrupt.cancel(task.pk)
            # Tell the executing agent to stop (best-effort, off the event loop).
            await sync_to_async(AgentConsumer.broadcast)(task.agent_id, messages.Cancel(task=str(task.pk)))
            await models.TaskEvent.objects.acreate(
                task=task,
                kind=enums.TaskEventKind.CANCELLED,
                message="Caller disconnected — task cascade-cancelled.",
            )
            task.is_done = True
            task.finished_at = timezone.now()
            task.latest_event_kind = enums.TaskEventKind.CANCELLED
            await task.asave(update_fields=["is_done", "finished_at", "latest_event_kind"])
            async for child in models.Task.objects.filter(parent_id=task.pk, is_done=False):
                stack.append(child)

    async def on_agent_log(self, agent_id: int, message: messages.Log) -> None:
        logging.info(f"Log Task {message}")

        await models.TaskEvent.objects.acreate(
            task_id=message.task,
            kind=enums.TaskEventKind.LOG,
            message=message.message,
        )

    async def on_agent_yield(self, agent_id: int, message: messages.Yield) -> None:
        logging.info(f"Yield Task {message}")

        await models.TaskEvent.objects.acreate(
            task_id=message.task,
            kind=enums.TaskEventKind.YIELD,
            returns=message.returns,
        )
        await self._unfold_to_higher_order(message.task, enums.TaskEventKind.YIELD, returns=message.returns)

    async def on_agent_done(self, agent_id: int, message: messages.Completed) -> None:
        logging.info(f"Critical Task {message}")

        self._progress_leases.cancel(message.task)
        self._auto_interrupt.cancel(message.task)
        x = await models.Task.objects.aget(id=message.task)
        if x.is_done:
            return  # dedup: a resent terminal report (the agent retries until EventAck)

        await models.TaskEvent.objects.acreate(
            task_id=message.task,
            kind=enums.TaskEventKind.COMPLETED,
        )

        x.is_done = True
        x.finished_at = timezone.now()
        x.latest_event_kind = enums.TaskEventKind.COMPLETED
        await x.asave(update_fields=["is_done", "finished_at", "latest_event_kind"])
        await self._unfold_to_higher_order(message.task, enums.TaskEventKind.COMPLETED)

    async def on_agent_cancelled(self, agent_id: int, message: messages.Cancelled) -> None:
        logging.info(f"Critical Task {message}")

        self._progress_leases.cancel(message.task)
        self._auto_interrupt.cancel(message.task)
        x = await models.Task.objects.aget(id=message.task)
        if x.is_done:
            return  # dedup: a resent terminal report (the agent retries until EventAck)

        await models.TaskEvent.objects.acreate(
            task_id=message.task,
            kind=enums.TaskEventKind.CANCELLED,
        )

        x.is_done = True
        x.finished_at = timezone.now()
        x.latest_event_kind = enums.TaskEventKind.CANCELLED
        await x.asave(update_fields=["is_done", "finished_at", "latest_event_kind"])
        await self._unfold_to_higher_order(message.task, enums.TaskEventKind.CANCELLED)

    async def on_agent_error(self, agent_id: int, message: messages.Failed) -> None:
        logging.info(f"Critical Task {message}")

        self._progress_leases.cancel(message.task)
        self._auto_interrupt.cancel(message.task)
        x = await models.Task.objects.aget(id=message.task)
        if x.is_done:
            return  # dedup: a resent terminal report (the agent retries until EventAck)

        await models.TaskEvent.objects.acreate(
            task_id=message.task,
            kind=enums.TaskEventKind.FAILED,
            message=message.error,
        )

        x.is_done = True
        x.finished_at = timezone.now()
        x.latest_event_kind = enums.TaskEventKind.FAILED
        await x.asave(update_fields=["is_done", "finished_at", "latest_event_kind"])
        await self._unfold_to_higher_order(message.task, enums.TaskEventKind.FAILED, message=message.error)

    async def on_agent_critical(self, agent_id: int, message: messages.Critical) -> None:
        logging.info(f"Criticial Task {message}")

        self._progress_leases.cancel(message.task)
        self._auto_interrupt.cancel(message.task)
        x = await models.Task.objects.aget(id=message.task)
        if x.is_done:
            return  # dedup: a resent terminal report (the agent retries until EventAck)

        await models.TaskEvent.objects.acreate(
            task_id=message.task,
            kind=enums.TaskEventKind.CRITICAL,
            message=message.error,
        )

        x.is_done = True
        x.finished_at = timezone.now()
        x.latest_event_kind = enums.TaskEventKind.CRITICAL
        await x.asave(update_fields=["is_done", "finished_at", "latest_event_kind"])
        await self._unfold_to_higher_order(message.task, enums.TaskEventKind.CRITICAL, message=message.error)

    async def on_agent_progress(self, agent_id: int, message: messages.Progress) -> None:
        logging.info(f"Progress Task {message}")

        await models.TaskEvent.objects.acreate(
            task_id=message.task,
            kind=enums.TaskEventKind.PROGRESS,
            progress=message.progress,
            message=message.message,
        )
        await self._arm_progress_lease(message.task)

    async def _arm_progress_lease(self, task_id: str) -> None:
        """(Re)arm the silent-physical-op lease for a physical task, if enabled."""
        lease = progress_lease_seconds()
        if lease <= 0:
            return  # disabled — zero overhead on the progress hot-path
        task = await models.Task.objects.select_related("implementation").aget(id=task_id)
        if task.is_done or task.implementation is None or task.implementation.effect != enums.EffectClassChoices.PHYSICAL.value:
            return
        self._progress_leases.schedule(task_id, lease, lambda: self.reconcile_silent_physical_op(task_id))

    async def reconcile_silent_physical_op(self, task_id: str | int) -> None:
        """Fail a physical task that reported progress then went silent. Pure DB op."""
        task = await models.Task.objects.aget(id=task_id)
        if task.is_done:
            return
        await models.TaskEvent.objects.acreate(
            task=task,
            kind=enums.TaskEventKind.CRITICAL,
            message="Physical op went silent past its progress lease — terminal, not retried.",
        )
        task.is_done = True
        task.finished_at = timezone.now()
        task.latest_event_kind = enums.TaskEventKind.CRITICAL
        await task.asave(update_fields=["is_done", "finished_at", "latest_event_kind"])

    async def on_agent_state_patch(self, agent_id: int, message: messages.StatePatch) -> None:
        logging.info(f"Log Patch for Task {message.state_name}")

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
            task_id=message.task_id,
            global_rev=message.global_rev,
        )

    async def on_agent_state_snapshot(self, agent_id: int, message: messages.StateSnapshot) -> None:
        logging.info(f"Log Snapshot for Task {agent_id}")

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

    async def on_agent_session_init(self, agent_id: int, message: messages.SessionInit) -> None:
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

    async def on_agent_lock(self, agent_id: int, message: messages.Lock) -> None:
        # Acquire: record that ``task`` holds lock ``key`` on this agent. Lock rows are
        # normally pre-created at registration; aupdate_or_create tolerates a missing one.
        # An unknown task is ignored (a stray lock must not tear down the transport, and
        # setting a dangling FK would raise IntegrityError → socket close).
        if not await models.Task.objects.filter(pk=message.task).aexists():
            logging.warning(f"Lock {message.key} requested by unknown task {message.task} — ignored")
            return
        await models.Lock.objects.aupdate_or_create(
            agent_id=agent_id,
            key=message.key,
            defaults={"hold_by_id": message.task},
        )

    async def on_agent_unlock(self, agent_id: int, message: messages.Unlock) -> None:
        # Release: clear the holder (no-op if the lock is absent or already free).
        await models.Lock.objects.filter(agent_id=agent_id, key=message.key).aupdate(hold_by=None)


persist_backend = ModelPersistBackend()
