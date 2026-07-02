"""Reclaim / grace / caller-death cascade — the concurrency core of the liveness model.

These drive the ``ModelPersistBackend`` port directly (a fresh instance per test isolates
its in-memory grace-timer registries) with seeded tasks and the pytest-django
``settings`` fixture to control the grace window. They target the session-match and
grace-expiry branches the plan flagged as the genuine concurrency risk.
"""

import asyncio

import pytest

from facade import enums, messages
from facade.messages import AgentMode
from facade.models import Task, TaskEvent
from facade.persist_backend import ModelPersistBackend

from tests.factories import build_task

pytestmark = [pytest.mark.django_db(transaction=True), pytest.mark.asyncio]


def _grace(settings, value):
    settings.REKUEST_GRACE = {"DEFAULT": value, "PER_MODE": {}, "PHYSICAL": value}


async def _event_kinds(ass_id):
    return [e.kind async for e in TaskEvent.objects.filter(task_id=ass_id)]


class TestExecutorReclaim:
    async def test_same_session_reconnect_reclaims(self, settings):
        _grace(settings, 30)
        ass = await build_task("recl-same")
        backend = ModelPersistBackend()
        agent_id = str(ass.agent_id)

        await backend.on_agent_connected(agent_id, "c1", session_id="S1")
        await backend.on_agent_disconnected(agent_id, "c1")
        assert agent_id in backend._executor_grace  # work held, not failed

        reclaimed = await backend.on_agent_connected(agent_id, "c2", session_id="S1")
        assert agent_id not in backend._executor_grace  # timer cancelled
        assert any(str(a.pk) == str(ass.pk) for a in reclaimed)  # handed back as inquiry

        assert enums.TaskEventKind.DISCONNECTED not in await _event_kinds(ass.pk)
        refreshed = await Task.objects.aget(pk=ass.pk)
        assert refreshed.is_done is False

    async def test_different_session_fails_orphaned_work(self, settings):
        _grace(settings, 30)
        ass = await build_task("recl-diff", effect="NONE")
        backend = ModelPersistBackend()
        agent_id = str(ass.agent_id)

        await backend.on_agent_connected(agent_id, "c1", session_id="S1")
        await backend.on_agent_disconnected(agent_id, "c1")
        # A fresh process (different session) took over: the old work is orphaned.
        reclaimed = await backend.on_agent_connected(agent_id, "c2", session_id="S2")

        assert reclaimed == []
        assert agent_id not in backend._executor_grace
        assert enums.TaskEventKind.DISCONNECTED in await _event_kinds(ass.pk)


class TestExecutorGraceExpiry:
    async def test_none_effect_expiry_is_recoverable_disconnected(self, settings):
        _grace(settings, 0.05)
        ass = await build_task("recl-exp-none", effect="NONE")
        backend = ModelPersistBackend()
        agent_id = str(ass.agent_id)

        await backend.on_agent_connected(agent_id, "c1", session_id="S1")
        await backend.on_agent_disconnected(agent_id, "c1")
        await asyncio.wait_for(backend._executor_grace[agent_id], timeout=2)

        assert enums.TaskEventKind.DISCONNECTED in await _event_kinds(ass.pk)
        refreshed = await Task.objects.aget(pk=ass.pk)
        assert refreshed.is_done is False  # none-effect is recoverable

    async def test_physical_effect_expiry_is_terminal_critical(self, settings):
        _grace(settings, 0.05)
        ass = await build_task("recl-exp-phys", effect="PHYSICAL")
        backend = ModelPersistBackend()
        agent_id = str(ass.agent_id)

        await backend.on_agent_connected(agent_id, "c1", session_id="S1")
        await backend.on_agent_disconnected(agent_id, "c1")
        await asyncio.wait_for(backend._executor_grace[agent_id], timeout=2)

        assert enums.TaskEventKind.CRITICAL in await _event_kinds(ass.pk)
        refreshed = await Task.objects.aget(pk=ass.pk)
        assert refreshed.is_done is True  # physical ambiguous failure is terminal

    async def test_reconnect_before_expiry_prevents_failure(self, settings):
        _grace(settings, 30)
        ass = await build_task("recl-noexp")
        backend = ModelPersistBackend()
        agent_id = str(ass.agent_id)
        await backend.on_agent_connected(agent_id, "c1", session_id="S1")
        await backend.on_agent_disconnected(agent_id, "c1")
        await backend.on_agent_connected(agent_id, "c2", session_id="S1")  # reclaim

        assert await _event_kinds(ass.pk) == []  # no failure event ever fired


class TestCallerDeath:
    async def test_caller_death_cascade_cancels_root_and_child(self, settings):
        _grace(settings, 0)  # inline cascade
        root = await build_task("cd-root", originating_connection_id="conn1")
        child = await build_task("cd-child", parent=root)
        backend = ModelPersistBackend()

        await backend.on_caller_disconnected(str(root.agent_id), "conn1", session_id=None, mode=AgentMode.CALLER.value)

        for a in (root, child):
            refreshed = await Task.objects.aget(pk=a.pk)
            assert refreshed.is_done is True
            assert refreshed.latest_event_kind == enums.TaskEventKind.CANCELLED

    async def test_observer_disconnect_does_not_cascade(self, settings):
        _grace(settings, 0)
        root = await build_task("cd-obs", originating_connection_id="conn1")
        backend = ModelPersistBackend()

        await backend.on_caller_disconnected(str(root.agent_id), "conn1", session_id=None, mode=AgentMode.OBSERVER.value)

        refreshed = await Task.objects.aget(pk=root.pk)
        assert refreshed.is_done is False

    async def test_caller_same_session_reconnect_reclaims_roots(self, settings):
        _grace(settings, 30)
        root = await build_task("cd-recl", originating_connection_id="conn1", originating_session_id="S1")
        backend = ModelPersistBackend()

        await backend.on_caller_disconnected(str(root.agent_id), "conn1", session_id="S1", mode=AgentMode.CALLER.value)
        assert "S1" in backend._caller_grace

        await backend.on_caller_connected(str(root.agent_id), "conn2", session_id="S1")
        assert "S1" not in backend._caller_grace  # timer cancelled

        refreshed = await Task.objects.aget(pk=root.pk)
        assert refreshed.is_done is False
        assert refreshed.originating_connection_id == "conn2"  # re-pointed to the new connection

    async def test_caller_grace_expiry_cancels_when_not_reclaimed(self, settings):
        _grace(settings, 0.05)
        root = await build_task("cd-exp", originating_connection_id="conn1", originating_session_id="S1")
        backend = ModelPersistBackend()

        await backend.on_caller_disconnected(str(root.agent_id), "conn1", session_id="S1", mode=AgentMode.CALLER.value)
        await asyncio.wait_for(backend._caller_grace["S1"], timeout=2)

        refreshed = await Task.objects.aget(pk=root.pk)
        assert refreshed.is_done is True
        assert refreshed.latest_event_kind == enums.TaskEventKind.CANCELLED


class TestProgressLease:
    async def test_silent_physical_op_fails_terminal(self, settings):
        settings.REKUEST_GRACE = {"DEFAULT": 0, "PER_MODE": {}, "PHYSICAL": 0, "PROGRESS_LEASE": 0.05}
        ass = await build_task("lease-phys", effect="PHYSICAL")
        backend = ModelPersistBackend()
        key = str(ass.pk)

        await backend.on_agent_progress("a", messages.Progress(task=key, progress=10))
        await asyncio.wait_for(backend._progress_leases[key], timeout=2)

        refreshed = await Task.objects.aget(pk=ass.pk)
        assert refreshed.is_done is True
        assert refreshed.latest_event_kind == enums.TaskEventKind.CRITICAL

    async def test_done_clears_lease_no_failure(self, settings):
        settings.REKUEST_GRACE = {"DEFAULT": 0, "PER_MODE": {}, "PHYSICAL": 0, "PROGRESS_LEASE": 30}
        ass = await build_task("lease-done", effect="PHYSICAL")
        backend = ModelPersistBackend()
        key = str(ass.pk)

        await backend.on_agent_progress("a", messages.Progress(task=key, progress=10))
        assert key in backend._progress_leases
        await backend.on_agent_done("a", messages.Completed(task=key))
        assert key not in backend._progress_leases  # lease cleared on terminal

    async def test_none_effect_has_no_lease(self, settings):
        settings.REKUEST_GRACE = {"DEFAULT": 0, "PER_MODE": {}, "PHYSICAL": 0, "PROGRESS_LEASE": 0.05}
        ass = await build_task("lease-none", effect="NONE")
        backend = ModelPersistBackend()
        key = str(ass.pk)

        await backend.on_agent_progress("a", messages.Progress(task=key, progress=10))
        assert key not in backend._progress_leases  # only physical work gets a lease


class TestIdempotentRedispatch:
    """The third level of the retry axis: PHYSICAL (terminal) < default (fate unknown) <
    idempotent (freely re-dispatchable — QUEUED + Assign re-broadcast into the agent queue,
    which retains messages for offline agents)."""

    @pytest.fixture
    def broadcasts(self, monkeypatch):
        from facade.consumers.async_consumer import AgentConsumer

        recorded = []
        monkeypatch.setattr(AgentConsumer, "broadcast", staticmethod(lambda agent_id, message: recorded.append((agent_id, message))))
        return recorded

    async def test_idempotent_expiry_requeues(self, settings, broadcasts):
        _grace(settings, 0.05)
        ass = await build_task("recl-idem", effect="NONE", idempotent=True)
        backend = ModelPersistBackend()
        agent_id = str(ass.agent_id)

        await backend.on_agent_connected(agent_id, "c1", session_id="S1")
        await backend.on_agent_disconnected(agent_id, "c1")
        await asyncio.wait_for(backend._executor_grace[agent_id], timeout=2)

        kinds = await _event_kinds(ass.pk)
        assert enums.TaskEventKind.QUEUED in kinds
        assert enums.TaskEventKind.DISCONNECTED not in kinds
        refreshed = await Task.objects.aget(pk=ass.pk)
        assert refreshed.is_done is False
        assert refreshed.latest_event_kind == enums.TaskEventKind.QUEUED

        assert len(broadcasts) == 1
        target_agent, message = broadcasts[0]
        assert isinstance(message, messages.Assign)
        assert message.task == str(ass.pk)
        assert message.args == (ass.args or {})
        assert message.reference == str(ass.reference)

    async def test_idempotent_physical_still_terminal(self, settings, broadcasts):
        _grace(settings, 0.05)
        ass = await build_task("recl-idem-phys", effect="PHYSICAL", idempotent=True)
        backend = ModelPersistBackend()
        agent_id = str(ass.agent_id)

        await backend.on_agent_connected(agent_id, "c1", session_id="S1")
        await backend.on_agent_disconnected(agent_id, "c1")
        await asyncio.wait_for(backend._executor_grace[agent_id], timeout=2)

        refreshed = await Task.objects.aget(pk=ass.pk)
        assert refreshed.is_done is True
        assert refreshed.latest_event_kind == enums.TaskEventKind.CRITICAL
        assert broadcasts == []

    async def test_sweep_is_reentrant_single_requeue(self, settings, broadcasts):
        _grace(settings, 30)
        ass = await build_task("recl-idem-sweep", effect="NONE", idempotent=True)
        backend = ModelPersistBackend()
        agent_id = str(ass.agent_id)

        await backend.on_agent_connected(agent_id, "c1", session_id="S1")
        await backend.on_agent_disconnected(agent_id, "c1")
        # The periodic sweep may reconcile repeatedly — only ONE requeue may result.
        await backend.reconcile_orphaned_executor_work(agent_id)
        await backend.reconcile_orphaned_executor_work(agent_id)

        kinds = await _event_kinds(ass.pk)
        assert kinds.count(enums.TaskEventKind.QUEUED) == 1
        assert len(broadcasts) == 1

    async def test_callerless_idempotent_falls_back_disconnected(self, settings, broadcasts):
        _grace(settings, 30)
        ass = await build_task("recl-idem-nocaller", effect="NONE", idempotent=True)
        await Task.objects.filter(pk=ass.pk).aupdate(caller=None)
        backend = ModelPersistBackend()
        agent_id = str(ass.agent_id)

        await backend.on_agent_connected(agent_id, "c1", session_id="S1")
        await backend.on_agent_disconnected(agent_id, "c1")
        await backend.reconcile_orphaned_executor_work(agent_id)

        kinds = await _event_kinds(ass.pk)
        assert enums.TaskEventKind.DISCONNECTED in kinds
        assert enums.TaskEventKind.QUEUED not in kinds
        assert broadcasts == []
