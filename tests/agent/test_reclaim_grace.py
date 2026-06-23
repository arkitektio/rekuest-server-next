"""Reclaim / grace / caller-death cascade — the concurrency core of the liveness model.

These drive the ``ModelPersistBackend`` port directly (a fresh instance per test isolates
its in-memory grace-timer registries) with seeded assignations and the pytest-django
``settings`` fixture to control the grace window. They target the session-match and
grace-expiry branches the plan flagged as the genuine concurrency risk.
"""

import asyncio

import pytest

from facade import enums, messages
from facade.messages import AgentMode
from facade.models import Assignation, AssignationEvent
from facade.persist_backend import ModelPersistBackend

from tests.factories import build_assignation

pytestmark = [pytest.mark.django_db(transaction=True), pytest.mark.asyncio]


def _grace(settings, value):
    settings.REKUEST_GRACE = {"DEFAULT": value, "PER_MODE": {}, "PHYSICAL": value}


async def _event_kinds(ass_id):
    return [e.kind async for e in AssignationEvent.objects.filter(assignation_id=ass_id)]


class TestExecutorReclaim:
    async def test_same_session_reconnect_reclaims(self, settings):
        _grace(settings, 30)
        ass = await build_assignation("recl-same")
        backend = ModelPersistBackend()
        agent_id = str(ass.agent_id)

        await backend.on_agent_connected(agent_id, "c1", session_id="S1")
        await backend.on_agent_disconnected(agent_id, "c1")
        assert agent_id in backend._executor_grace  # work held, not failed

        reclaimed = await backend.on_agent_connected(agent_id, "c2", session_id="S1")
        assert agent_id not in backend._executor_grace  # timer cancelled
        assert any(str(a.pk) == str(ass.pk) for a in reclaimed)  # handed back as inquiry

        assert enums.AssignationEventKind.DISCONNECTED not in await _event_kinds(ass.pk)
        refreshed = await Assignation.objects.aget(pk=ass.pk)
        assert refreshed.is_done is False

    async def test_different_session_fails_orphaned_work(self, settings):
        _grace(settings, 30)
        ass = await build_assignation("recl-diff", effect="NONE")
        backend = ModelPersistBackend()
        agent_id = str(ass.agent_id)

        await backend.on_agent_connected(agent_id, "c1", session_id="S1")
        await backend.on_agent_disconnected(agent_id, "c1")
        # A fresh process (different session) took over: the old work is orphaned.
        reclaimed = await backend.on_agent_connected(agent_id, "c2", session_id="S2")

        assert reclaimed == []
        assert agent_id not in backend._executor_grace
        assert enums.AssignationEventKind.DISCONNECTED in await _event_kinds(ass.pk)


class TestExecutorGraceExpiry:
    async def test_none_effect_expiry_is_recoverable_disconnected(self, settings):
        _grace(settings, 0.05)
        ass = await build_assignation("recl-exp-none", effect="NONE")
        backend = ModelPersistBackend()
        agent_id = str(ass.agent_id)

        await backend.on_agent_connected(agent_id, "c1", session_id="S1")
        await backend.on_agent_disconnected(agent_id, "c1")
        await asyncio.wait_for(backend._executor_grace[agent_id], timeout=2)

        assert enums.AssignationEventKind.DISCONNECTED in await _event_kinds(ass.pk)
        refreshed = await Assignation.objects.aget(pk=ass.pk)
        assert refreshed.is_done is False  # none-effect is recoverable

    async def test_physical_effect_expiry_is_terminal_critical(self, settings):
        _grace(settings, 0.05)
        ass = await build_assignation("recl-exp-phys", effect="PHYSICAL")
        backend = ModelPersistBackend()
        agent_id = str(ass.agent_id)

        await backend.on_agent_connected(agent_id, "c1", session_id="S1")
        await backend.on_agent_disconnected(agent_id, "c1")
        await asyncio.wait_for(backend._executor_grace[agent_id], timeout=2)

        assert enums.AssignationEventKind.CRITICAL in await _event_kinds(ass.pk)
        refreshed = await Assignation.objects.aget(pk=ass.pk)
        assert refreshed.is_done is True  # physical ambiguous failure is terminal

    async def test_reconnect_before_expiry_prevents_failure(self, settings):
        _grace(settings, 30)
        ass = await build_assignation("recl-noexp")
        backend = ModelPersistBackend()
        agent_id = str(ass.agent_id)
        await backend.on_agent_connected(agent_id, "c1", session_id="S1")
        await backend.on_agent_disconnected(agent_id, "c1")
        await backend.on_agent_connected(agent_id, "c2", session_id="S1")  # reclaim

        assert await _event_kinds(ass.pk) == []  # no failure event ever fired


class TestCallerDeath:
    async def test_caller_death_cascade_cancels_root_and_child(self, settings):
        _grace(settings, 0)  # inline cascade
        root = await build_assignation("cd-root", originating_connection_id="conn1")
        child = await build_assignation("cd-child", parent=root)
        backend = ModelPersistBackend()

        await backend.on_caller_disconnected(str(root.agent_id), "conn1", session_id=None, mode=AgentMode.CALLER.value)

        for a in (root, child):
            refreshed = await Assignation.objects.aget(pk=a.pk)
            assert refreshed.is_done is True
            assert refreshed.latest_event_kind == enums.AssignationEventKind.CANCELLED

    async def test_observer_disconnect_does_not_cascade(self, settings):
        _grace(settings, 0)
        root = await build_assignation("cd-obs", originating_connection_id="conn1")
        backend = ModelPersistBackend()

        await backend.on_caller_disconnected(str(root.agent_id), "conn1", session_id=None, mode=AgentMode.OBSERVER.value)

        refreshed = await Assignation.objects.aget(pk=root.pk)
        assert refreshed.is_done is False

    async def test_caller_same_session_reconnect_reclaims_roots(self, settings):
        _grace(settings, 30)
        root = await build_assignation("cd-recl", originating_connection_id="conn1", originating_session_id="S1")
        backend = ModelPersistBackend()

        await backend.on_caller_disconnected(str(root.agent_id), "conn1", session_id="S1", mode=AgentMode.CALLER.value)
        assert "S1" in backend._caller_grace

        await backend.on_caller_connected(str(root.agent_id), "conn2", session_id="S1")
        assert "S1" not in backend._caller_grace  # timer cancelled

        refreshed = await Assignation.objects.aget(pk=root.pk)
        assert refreshed.is_done is False
        assert refreshed.originating_connection_id == "conn2"  # re-pointed to the new connection

    async def test_caller_grace_expiry_cancels_when_not_reclaimed(self, settings):
        _grace(settings, 0.05)
        root = await build_assignation("cd-exp", originating_connection_id="conn1", originating_session_id="S1")
        backend = ModelPersistBackend()

        await backend.on_caller_disconnected(str(root.agent_id), "conn1", session_id="S1", mode=AgentMode.CALLER.value)
        await asyncio.wait_for(backend._caller_grace["S1"], timeout=2)

        refreshed = await Assignation.objects.aget(pk=root.pk)
        assert refreshed.is_done is True
        assert refreshed.latest_event_kind == enums.AssignationEventKind.CANCELLED


class TestProgressLease:
    async def test_silent_physical_op_fails_terminal(self, settings):
        settings.REKUEST_GRACE = {"DEFAULT": 0, "PER_MODE": {}, "PHYSICAL": 0, "PROGRESS_LEASE": 0.05}
        ass = await build_assignation("lease-phys", effect="PHYSICAL")
        backend = ModelPersistBackend()
        key = str(ass.pk)

        await backend.on_agent_progress("a", messages.Progress(assignation=key, progress=10))
        await asyncio.wait_for(backend._progress_leases[key], timeout=2)

        refreshed = await Assignation.objects.aget(pk=ass.pk)
        assert refreshed.is_done is True
        assert refreshed.latest_event_kind == enums.AssignationEventKind.CRITICAL

    async def test_done_clears_lease_no_failure(self, settings):
        settings.REKUEST_GRACE = {"DEFAULT": 0, "PER_MODE": {}, "PHYSICAL": 0, "PROGRESS_LEASE": 30}
        ass = await build_assignation("lease-done", effect="PHYSICAL")
        backend = ModelPersistBackend()
        key = str(ass.pk)

        await backend.on_agent_progress("a", messages.Progress(assignation=key, progress=10))
        assert key in backend._progress_leases
        await backend.on_agent_done("a", messages.Completed(assignation=key))
        assert key not in backend._progress_leases  # lease cleared on terminal

    async def test_none_effect_has_no_lease(self, settings):
        settings.REKUEST_GRACE = {"DEFAULT": 0, "PER_MODE": {}, "PHYSICAL": 0, "PROGRESS_LEASE": 0.05}
        ass = await build_assignation("lease-none", effect="NONE")
        backend = ModelPersistBackend()
        key = str(ass.pk)

        await backend.on_agent_progress("a", messages.Progress(assignation=key, progress=10))
        assert key not in backend._progress_leases  # only physical work gets a lease
