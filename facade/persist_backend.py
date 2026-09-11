import logging
from typing import List, Optional, Tuple

from asgiref.sync import sync_to_async
from channels.db import database_sync_to_async
from django.db import transaction
from django.utils import timezone

from facade import inputs, liveness, models, enums, messages
from facade.probes.persist import probe_event_backend
from facade.grace import GraceScheduler, grace_seconds, progress_lease_seconds
from facade.higher_order import project_returns
from facade.ports import LeaseClaim

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

    Writes to an agent's liveness columns follow one rule (see :mod:`facade.liveness`):
    **transitions** (claim / release / revoke) take a row lock and go through ``save()`` so
    ``agent_post_save`` fires; **renewal** (the heartbeat, the only hot path) is a lock-free
    compare-and-set on ``lease_epoch`` whose rowcount is the answer.
    """

    def __init__(self) -> None:
        # Responsive reconcile triggers (in-memory; the DB is authoritative). Keyed:
        # ``_executor_grace`` by agent id (agent death → fail its executed work);
        # ``_progress_leases`` by task id (silent physical op).
        self._executor_grace = GraceScheduler()
        self._progress_leases = GraceScheduler()
        # auto_interrupt escalation timers (keyed by task id): a cancel with an
        # auto_interrupt window escalates to an interrupt if not confirmed in time.
        self._auto_interrupt = GraceScheduler()

    async def _unfold_to_higher_order(
        self,
        child_task_id: str,
        kind,
        returns: Optional[dict] = None,
        message: Optional[str] = None,
        task: Optional[models.Task] = None,
    ) -> None:
        """If this task is the child of a higher-order wrapper, re-emit a mapped event on it.

        The lower implementation runs on a child task; the user watches the wrapper. So we
        project the child's returns back onto the wrapper's return ports and emit the corresponding
        event on the wrapper (linked via ``delegated_to``), which the subscription layer broadcasts.
        Non-higher-order children (hooks, dependency sub-assignments) are ignored.

        The overwhelmingly common case is an ordinary task, so the ``is_higher_order_child``
        flag gates the parent join: handlers that already hold the row pass ``task`` (zero
        extra queries); the fire-and-forget Yield path does one slim flag read instead of
        the two-table ``select_related`` it used to run on every yield.
        """
        if task is not None:
            if not task.is_higher_order_child:
                return
        else:
            try:
                is_higher_order_child = await models.Task.objects.values_list("is_higher_order_child", flat=True).aget(id=child_task_id)
            except models.Task.DoesNotExist:
                return
            if not is_higher_order_child:
                return

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

        # Probes fail fast — hover-grade work is worthless once its executor is
        # gone, so no grace window applies to them (tasks keep theirs below).
        await probe_event_backend.fail_all_for_agent(agent_id)

        # Grace window: instead of failing in-flight work immediately, wait — a brief blip
        # that reconnects with the same session reclaims it (on_agent_connected cancels the
        # timer). grace<=0 keeps the legacy immediate, inline behaviour (deterministic).
        grace = grace_seconds()
        if grace <= 0:
            await self.reconcile_orphaned_executor_work(agent_id)
            return

        self._executor_grace.schedule(agent_id, grace, lambda: self.reconcile_orphaned_executor_work(agent_id))

    async def reconcile_orphaned_executor_work(self, agent_id: int) -> None:
        """Fail an agent's in-flight work after a confirmed loss. Pure, idempotent DB op.

        The authoritative reconcile shared by all three triggers (grace timer, reconnect with
        a fresh session, and the periodic sweep). No-op if the agent is live again — a
        reconnect in the meantime means the work is being reclaimed, not orphaned.

        The bail-out asks :func:`liveness.agent_is_live`, not ``agent.connected``. Every other
        liveness decision goes through that one predicate, and this used to be the exception:
        a stuck-connected agent whose lease had expired would make this a silent no-op, so its
        work stayed ``is_done=False`` forever. Today the sweep happens to revoke (flipping
        ``connected``) *before* calling here, which masks it — but that is sequencing luck, not
        a guarantee, and it breaks the moment a new trigger calls this directly.
        """
        agent = await models.Agent.objects.aget(id=agent_id)
        if liveness.agent_is_live(agent.connected, agent.last_seen):
            return
        in_flight = [a async for a in models.Task.objects.select_related("implementation", "action").filter(agent_id=agent_id, is_done=False)]
        await self._fail_and_cascade_inflight(in_flight)

    def _revoke_lease_sync(self, agent_id: int) -> bool:
        """Revoke one stuck-connected agent's lease under a row lock. Returns whether we won.

        Re-checks staleness *under the lock*, so this doubles as the claim that makes the sweep
        multi-worker safe: whichever worker gets the lock first flips ``connected`` and the
        others then see a row that is no longer stale and back off, instead of every worker
        racing on to ``reconcile_orphaned_executor_work`` and emitting duplicate terminal
        events. A reconnect that landed between the scan and the lock also lands here.

        Bumping ``lease_epoch`` is the part a boolean cannot express: it *fences* the wedged
        connection, so if that worker's event loop later resumes, its heartbeat renewal
        compare-and-set matches no row and it closes itself instead of resurrecting an agent
        whose in-flight work has already been failed.

        Uses ``Model.save()`` (NOT ``.aupdate``) so ``agent_post_save`` fires and the GraphQL
        agent/``active`` subscriptions + dashboards refresh to reality. ``last_seen`` and
        ``active_connection_id`` are deliberately left untouched: ``last_seen`` is the true
        last-contact time the orphan cutoff depends on, and clearing ``active_connection_id``
        could let a still-wedged socket's later disconnect pass the generation guard.
        """
        with transaction.atomic():
            agent = models.Agent.objects.select_for_update().get(id=agent_id)
            if not liveness.agent_is_stale(agent.connected, agent.last_seen):
                return False  # healed or reconnected while we waited for the lock
            agent.connected = False
            agent.lease_epoch += 1
            agent.save(update_fields=["connected", "lease_epoch"])
        return True

    async def reconcile_stale_agents(self) -> int:
        """Heal websocket agents whose ``connected`` is stuck True past the stale window.

        The disconnect handler only runs on a clean socket close; a crashed/killed worker leaves
        ``connected=True`` with a stale ``last_seen`` forever, and the in-memory grace timers die
        with the process. This is the DB-authoritative safety net: revoke the lease
        (``connected=False`` + epoch bump) and reconcile the orphaned in-flight work.

        Idempotent and multi-worker-safe: the revoke is a lock-guarded claim, so only the worker
        that actually flips a row goes on to reconcile it. Driven by both the in-process reaper
        loop and the ``reconcile_tasks`` management command. Returns the number healed.
        """
        stale = [
            a
            async for a in models.Agent.objects.select_related("organization")
            .filter(kind=enums.AgentKind.WEBSOCKET.value)
            .filter(liveness.stale_agent_q(prefix=""))
        ]
        healed = 0
        for agent in stale:
            if not await database_sync_to_async(self._revoke_lease_sync)(agent.pk):
                continue  # another worker's sweep (or a reconnect) got there first
            await probe_event_backend.fail_all_for_agent(agent.pk)  # calls fail fast, no grace
            await self.reconcile_orphaned_executor_work(agent.pk)  # now matches connected=False
            healed += 1
        return healed

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

    def _claim_task_transition_sync(self, task_id: int, *, to_kind: str, mark_done: bool = False, skip_if_kind: str | None = None) -> bool:
        """Take an orphaned task's terminal transition under a row lock. Returns whether we won.

        The sweep is re-entrant *and* runs concurrently in every daphne process, so "is this
        task still in-flight?" must be answered and acted on atomically. Reading the flag and
        then writing it — as this path used to — lets two workers both observe an in-flight task
        and both emit a terminal ``TaskEvent`` for it. Losing the claim (already done, or
        already in ``skip_if_kind``) means another trigger handled this task; skip it silently.

        ``save()`` rather than ``.aupdate()``: a task transition is observable, and
        ``task_post_save`` fans it out to the agent/child task feeds.
        """
        with transaction.atomic():
            task = models.Task.objects.select_for_update().get(pk=task_id)
            if task.is_done or (skip_if_kind is not None and task.latest_event_kind == skip_if_kind):
                return False
            task.latest_event_kind = to_kind
            update_fields = ["latest_event_kind"]
            if mark_done:
                task.is_done = True
                task.finished_at = timezone.now()
                update_fields += ["is_done", "finished_at"]
            task.save(update_fields=update_fields)
        return True

    async def _fail_and_cascade_inflight(self, tasks: List[models.Task]) -> None:
        """Mark orphaned in-flight work along the retry axis.

        ``effect:physical`` failed ambiguously (the executor vanished) → CRITICAL (terminal,
        never retried). Idempotent actions → QUEUED + the Assign re-broadcast into the
        agent's redis queue (which retains messages for offline agents), so the work re-runs
        on reconnect — a same-session reclaim after grace expiry may double-execute, which is
        safe by the idempotent contract. Everything else → DISCONNECTED (fate unknown,
        recoverable but never automatically resolved).

        Every branch claims the transition first and only emits its ``TaskEvent`` if it won, so
        concurrent sweeps produce exactly one terminal event per task rather than one each.
        """
        from facade.consumers.async_consumer import AgentConsumer  # lazy: avoids import cycle

        for task in tasks:
            self._auto_interrupt.cancel(task.pk)
            implementation = task.implementation
            effect = implementation.effect if implementation is not None else enums.EffectClassChoices.NONE.value
            if effect == enums.EffectClassChoices.PHYSICAL.value:
                if not await database_sync_to_async(self._claim_task_transition_sync)(task.pk, to_kind=enums.TaskEventKind.CRITICAL, mark_done=True):
                    continue
                await models.TaskEvent.objects.acreate(
                    task=task,
                    kind=enums.TaskEventKind.CRITICAL,
                    message="Executor lost while running physical-effect work — terminal, not retried.",
                )
                continue

            # The ``!= QUEUED`` guard makes the periodic sweep re-entrant: reconciling an
            # already-requeued task again must not pile duplicate Assigns into the queue. The
            # in-memory read here is only a cheap early-out; the claim below is authoritative.
            if task.action is not None and task.action.idempotent and task.latest_event_kind != enums.TaskEventKind.QUEUED:
                # Built BEFORE the claim: if there is no re-dispatchable identity we must fall
                # through to the fate-unknown branch, not leave the task marked QUEUED.
                assign_message = await database_sync_to_async(self._build_redispatch_assign_sync)(task.pk)
                if assign_message is not None:
                    if not await database_sync_to_async(self._claim_task_transition_sync)(
                        task.pk, to_kind=enums.TaskEventKind.QUEUED, skip_if_kind=enums.TaskEventKind.QUEUED
                    ):
                        continue
                    await models.TaskEvent.objects.acreate(
                        task=task,
                        kind=enums.TaskEventKind.QUEUED,
                        message="Executor lost — idempotent action re-queued for redelivery.",
                    )
                    await sync_to_async(AgentConsumer.broadcast)(task.agent_id, assign_message)
                    continue
                # No re-dispatchable identity → fall through to fate-unknown.

            if not await database_sync_to_async(self._claim_task_transition_sync)(
                task.pk, to_kind=enums.TaskEventKind.DISCONNECTED, skip_if_kind=enums.TaskEventKind.DISCONNECTED
            ):
                continue
            await models.TaskEvent.objects.acreate(
                task=task,
                kind=enums.TaskEventKind.DISCONNECTED,
                message="Agent disconnected. Fate unknown",
            )

    def _claim_lease_sync(self, agent_id: int, connection_id: str | None, session_id: str | None, force: bool) -> Tuple[bool, Optional[int], Optional[str], bool]:
        """Atomically decide the executor singleton and take the lease. Returns
        ``(claimed, epoch, prior_session, displaced_incumbent)``.

        The gate and the write happen under one ``select_for_update`` so they cannot be split:
        previously the gate read ``connected``/``last_seen`` off an instance loaded during
        authentication and the write re-fetched afterwards, so two concurrent registrations on
        different workers could both observe the same stale incumbent, both pass, and both be
        handed the in-flight work as ``Init`` inquiries.

        Gate: reject only a *provably live* incumbent (``connected`` AND a fresh heartbeat)
        when ``force`` is not set. A STALE incumbent — ``connected`` stuck True but the lease
        expired (crashed worker, lost in-memory timers) — is displaced without ``force``, so a
        dead connection never wedges the agent behind a ``--force`` reconnect.

        Bumping ``lease_epoch`` is what fences the previous owner: its next heartbeat renewal
        compare-and-sets against an epoch that no longer exists, matches no row, and it closes.
        """
        with transaction.atomic():
            agent = models.Agent.objects.select_for_update().get(id=agent_id)
            if liveness.agent_is_live(agent.connected, agent.last_seen) and not force:
                return False, None, agent.active_session_id, False

            prior_session = agent.active_session_id
            displaced_incumbent = agent.connected

            agent.lease_epoch += 1
            agent.connected = True
            agent.last_seen = timezone.now()
            agent.active_connection_id = connection_id
            agent.active_session_id = session_id
            agent.save(update_fields=["lease_epoch", "connected", "last_seen", "active_connection_id", "active_session_id"])

        return True, agent.lease_epoch, prior_session, displaced_incumbent

    async def on_agent_connected(self, agent_id: int, connection_id: str | None = None, session_id: str | None = None, force: bool = False) -> LeaseClaim:
        claimed, epoch, prior_session, displaced_incumbent = await database_sync_to_async(self._claim_lease_sync)(agent_id, connection_id, session_id, force)
        if not claimed:
            return LeaseClaim(claimed=False)

        # We are deciding reclaim-vs-cascade now, so cancel any pending grace timer.
        self._executor_grace.cancel(agent_id)

        in_flight = [a async for a in models.Task.objects.select_related("implementation", "action").filter(agent_id=agent_id, is_done=False)]

        # A different session means a FRESH process took over (the old one died): the prior
        # in-flight work is orphaned and must fail-and-cascade rather than be reclaimed.
        if prior_session is not None and session_id is not None and prior_session != session_id:
            await self._fail_and_cascade_inflight(in_flight)
            return LeaseClaim(claimed=True, epoch=epoch, tasks=[], displaced_incumbent=displaced_incumbent)

        # Same session (or first connect / no session info) → reclaim: hand the in-flight
        # work back as inquiries so the surviving process can re-sync.
        return LeaseClaim(claimed=True, epoch=epoch, tasks=in_flight, displaced_incumbent=displaced_incumbent)

    async def renew_agent_lease(self, agent_id: int, lease_epoch: int) -> bool:
        """Renew the executor lease — the hot path, once per heartbeat per agent.

        A lock-free compare-and-set: the rowcount *is* the answer to "am I still the owner?".
        Returns False when this connection has been displaced by a newer registration or
        revoked by the stale sweep (either bumps ``lease_epoch``); the caller must then close,
        because a connection that cannot renew must not keep executing work.

        Deliberately ``.aupdate()`` rather than ``save()``: nothing observable transitions on a
        renewal, so this must NOT fire ``agent_post_save`` — that would broadcast an
        ``AgentChange`` to the whole organization every ``AGENT_HEARTBEAT_INTERVAL`` per agent.
        """
        rows = await models.Agent.objects.filter(id=agent_id, lease_epoch=lease_epoch).aupdate(last_seen=timezone.now())
        return rows == 1

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
        connection_id: str | None = None,
        session_id: str | None = None,
    ) -> Tuple[models.Task, bool]:
        """Assign *dependent* work requested by an agent over the socket.

        Idempotent on ``(caller, reference)`` and durable-before-return: a resend of the same
        ``reference`` returns the existing task with ``created=False`` rather than creating a
        duplicate. Raises ``PermissionError`` for a parentless (root) assign — roots must trace
        to an accountable human, so they originate solely from the GraphQL ``assign`` mutation
        (see the human-root invariant in ``facade.provenance``). Runs the sync postman backend
        off the event loop.
        """
        return await database_sync_to_async(self._caller_assign_sync)(agent_id, message, connection_id, session_id)

    def _caller_assign_sync(
        self,
        agent_id: int,
        message: messages.AssignRequest,
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

        if message.parent is None:
            raise PermissionError("An agent may only assign dependent work: 'parent' is required. Root tasks originate from the GraphQL assign mutation, where the initiator is an accountable human.")

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
            step=message.step,
        )
        # A dependent task's fate follows its parent, so nothing about this connection needs
        # recording on the row: if this agent dies, the executor-death cascade covers its work,
        # and if the parent's tree is cancelled the child goes with it.
        return controll_backend.assign(ctx, assign_input), True

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
            "cancel": lambda: controll_backend.cancel(inputs.CancelInputModel(task=ref), caller=caller),
            "interrupt": lambda: controll_backend.interrupt(inputs.InterruptInputModel(task=ref), caller=caller),
            "pause": lambda: controll_backend.pause(inputs.PauseInputModel(task=ref), caller=caller),
            "resume": lambda: controll_backend.resume(inputs.ResumeInputModel(task=ref, step=step), caller=caller),
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
    async def _agent_task(self, agent_id: int, task_id: str) -> models.Task | None:
        """Fetch a task, asserting it belongs to the reporting agent.

        The agent's *socket* is authenticated, but the task id inside the frame is not — it is
        whatever the agent put there. Without the ``agent_id`` predicate any authenticated agent
        could terminate, fail, or inject results into any task in any organization simply by
        naming its id. ``Task.agent`` is non-nullable and set at dispatch, so this is total.

        Returns ``None`` when the task is unknown *or* not this agent's, which callers treat the
        same way: drop the frame rather than tear down the transport.
        """
        try:
            return await models.Task.objects.aget(id=task_id, agent_id=agent_id)
        except models.Task.DoesNotExist:
            logging.warning(f"Agent {agent_id} reported on task {task_id}, which is not assigned to it. Dropping.")
            return None

    async def on_agent_interrupted(self, agent_id: int, message: messages.Interrupted) -> None:
        self._progress_leases.cancel(message.task)
        self._auto_interrupt.cancel(message.task)
        x = await self._agent_task(agent_id, message.task)
        if x is None:
            return
        if x.is_done:
            return
        await models.TaskEvent.objects.acreate(task=x, kind=enums.TaskEventKind.INTERRUPTED)
        x.is_done = True
        x.finished_at = timezone.now()
        x.latest_event_kind = enums.TaskEventKind.INTERRUPTED
        await x.asave(update_fields=["is_done", "finished_at", "latest_event_kind"])
        await self._unfold_to_higher_order(message.task, enums.TaskEventKind.INTERRUPTED, task=x)

    async def _on_nonterminal_confirm(self, agent_id: int, task_id: str, kind, *, cancel_lease: bool = False) -> None:
        """Persist a non-terminal lifecycle confirmation (paused/resumed)."""
        if cancel_lease:
            self._progress_leases.cancel(task_id)
        # A confirmation for an unknown task — or another agent's task — must not tear down the
        # transport; it is dropped.
        x = await self._agent_task(agent_id, task_id)
        if x is None:
            return
        if x.is_done:
            return
        await models.TaskEvent.objects.acreate(task=x, kind=kind)
        x.latest_event_kind = kind
        await x.asave(update_fields=["latest_event_kind"])

    async def on_agent_paused(self, agent_id: int, message: messages.Paused) -> None:
        # A suspended op stops reporting progress — don't let the silent-physical-op lease reap it.
        await self._on_nonterminal_confirm(agent_id, message.task, enums.TaskEventKind.PAUSED, cancel_lease=True)

    async def on_agent_resumed(self, agent_id: int, message: messages.Resumed) -> None:
        await self._on_nonterminal_confirm(agent_id, message.task, enums.TaskEventKind.RESUMED)

    async def on_agent_started(self, agent_id: int, message: messages.Started) -> None:
        # The agent accepted and began executing — record it (mirrored to the caller as StartedEvent).
        await self._on_nonterminal_confirm(agent_id, message.task, enums.TaskEventKind.STARTED)

    async def on_agent_log(self, agent_id: int, message: messages.Log) -> None:
        logging.info(f"Log Task {message}")

        if await self._agent_task(agent_id, message.task) is None:
            return
        await models.TaskEvent.objects.acreate(
            task_id=message.task,
            kind=enums.TaskEventKind.LOG,
            message=message.message,
            level=message.level,
        )

    async def on_agent_yield(self, agent_id: int, message: messages.Yield) -> None:
        logging.info(f"Yield Task {message}")

        if await self._agent_task(agent_id, message.task) is None:
            return
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
        x = await self._agent_task(agent_id, message.task)
        if x is None:
            return
        if x.is_done:
            return  # dedup: a resent terminal report (the agent retries until EventAck)

        await models.TaskEvent.objects.acreate(task=x, kind=enums.TaskEventKind.COMPLETED)

        x.is_done = True
        x.finished_at = timezone.now()
        x.latest_event_kind = enums.TaskEventKind.COMPLETED
        await x.asave(update_fields=["is_done", "finished_at", "latest_event_kind"])
        await self._unfold_to_higher_order(message.task, enums.TaskEventKind.COMPLETED, task=x)

    async def on_agent_cancelled(self, agent_id: int, message: messages.Cancelled) -> None:
        logging.info(f"Critical Task {message}")

        self._progress_leases.cancel(message.task)
        self._auto_interrupt.cancel(message.task)
        x = await self._agent_task(agent_id, message.task)
        if x is None:
            return
        if x.is_done:
            return  # dedup: a resent terminal report (the agent retries until EventAck)

        await models.TaskEvent.objects.acreate(task=x, kind=enums.TaskEventKind.CANCELLED)

        x.is_done = True
        x.finished_at = timezone.now()
        x.latest_event_kind = enums.TaskEventKind.CANCELLED
        await x.asave(update_fields=["is_done", "finished_at", "latest_event_kind"])
        await self._unfold_to_higher_order(message.task, enums.TaskEventKind.CANCELLED, task=x)

    async def on_agent_error(self, agent_id: int, message: messages.Failed) -> None:
        logging.info(f"Critical Task {message}")

        self._progress_leases.cancel(message.task)
        self._auto_interrupt.cancel(message.task)
        x = await self._agent_task(agent_id, message.task)
        if x is None:
            return
        if x.is_done:
            return  # dedup: a resent terminal report (the agent retries until EventAck)

        await models.TaskEvent.objects.acreate(task=x, kind=enums.TaskEventKind.FAILED, message=message.error)

        x.is_done = True
        x.finished_at = timezone.now()
        x.latest_event_kind = enums.TaskEventKind.FAILED
        await x.asave(update_fields=["is_done", "finished_at", "latest_event_kind"])
        await self._unfold_to_higher_order(message.task, enums.TaskEventKind.FAILED, message=message.error, task=x)

    async def on_agent_critical(self, agent_id: int, message: messages.Critical) -> None:
        logging.info(f"Criticial Task {message}")

        self._progress_leases.cancel(message.task)
        self._auto_interrupt.cancel(message.task)
        x = await self._agent_task(agent_id, message.task)
        if x is None:
            return
        if x.is_done:
            return  # dedup: a resent terminal report (the agent retries until EventAck)

        await models.TaskEvent.objects.acreate(task=x, kind=enums.TaskEventKind.CRITICAL, message=message.error)

        x.is_done = True
        x.finished_at = timezone.now()
        x.latest_event_kind = enums.TaskEventKind.CRITICAL
        await x.asave(update_fields=["is_done", "finished_at", "latest_event_kind"])
        await self._unfold_to_higher_order(message.task, enums.TaskEventKind.CRITICAL, message=message.error, task=x)

    async def on_agent_progress(self, agent_id: int, message: messages.Progress) -> None:
        logging.info(f"Progress Task {message}")

        if await self._agent_task(agent_id, message.task) is None:
            return
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
        # One EXISTS instead of a two-table row fetch — this runs per Progress report.
        is_live_physical = await models.Task.objects.filter(
            id=task_id,
            is_done=False,
            implementation__effect=enums.EffectClassChoices.PHYSICAL.value,
        ).aexists()
        if not is_live_physical:
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
