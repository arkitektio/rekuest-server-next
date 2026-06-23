"""Refactor surface: typed port conformance, the delivery seam, pure reconcile ops, the sweep.

These pin the new abstractions the real-time refactor introduced. The existing
``test_reclaim_grace.py`` still exercises the *timer* trigger over the same reconcile ops;
here we call the ops directly (no timers) and drive the DB-sweep management command.
"""

from datetime import timedelta
from io import StringIO

import pytest
from django.core.management import call_command
from django.utils import timezone

from facade import enums, messages, transport
from facade.ports import PersistBackend
from facade.persist_backend import ModelPersistBackend, persist_backend

from tests.factories import build_task, build_webhook_agent


def test_persist_backend_satisfies_port():
    # runtime_checkable Protocol: the concrete backend exposes the whole port surface.
    assert isinstance(persist_backend, PersistBackend)


def test_deliver_to_agent_routes_by_kind(monkeypatch):
    pushed, posted = [], []
    monkeypatch.setattr(transport.RedisAgentQueue, "from_settings", classmethod(lambda cls: type("Q", (), {"push": lambda self, a, b: pushed.append((a, b))})()))
    monkeypatch.setattr(transport.hooks, "deliver_to_hook", lambda agent, body: posted.append((agent, body)))

    ws = type("A", (), {"pk": 7, "kind": enums.AgentKind.WEBSOCKET.value})()
    hook = type("A", (), {"pk": 8, "kind": enums.AgentKind.WEBHOOK.value})()
    msg = messages.Cancel(task="a1")

    transport.deliver_to_agent(ws, msg)
    transport.deliver_to_agent(hook, msg)

    assert len(pushed) == 1 and pushed[0][0] == "7"
    assert len(posted) == 1 and posted[0][0] is hook


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
class TestReconcileOps:
    async def test_reconcile_orphaned_executor_work_is_effect_aware(self):
        none_ass = await build_task("rec-none", effect="NONE")
        phys_ass = await build_task("rec-phys", effect="PHYSICAL")
        backend = ModelPersistBackend()

        # Mark both agents disconnected (the reconcile op no-ops a connected agent).
        from facade.models import Agent

        for ass in (none_ass, phys_ass):
            await Agent.objects.filter(pk=ass.agent_id).aupdate(connected=False)
            await backend.reconcile_orphaned_executor_work(ass.agent_id)

        none_ass = await type(none_ass).objects.aget(pk=none_ass.pk)
        phys_ass = await type(phys_ass).objects.aget(pk=phys_ass.pk)
        assert none_ass.latest_event_kind == enums.TaskEventKind.DISCONNECTED and none_ass.is_done is False
        assert phys_ass.latest_event_kind == enums.TaskEventKind.CRITICAL and phys_ass.is_done is True

    async def test_reconcile_caller_roots_cancels(self):
        root = await build_task("rec-caller", originating_connection_id="connX")
        backend = ModelPersistBackend()

        await backend.reconcile_caller_roots("connX", None)

        root = await type(root).objects.aget(pk=root.pk)
        assert root.is_done is True and root.latest_event_kind == enums.TaskEventKind.CANCELLED


@pytest.mark.django_db(transaction=True)
class TestReconcileSweep:
    def test_sweep_fails_stale_disconnected_executor_work(self, settings):
        settings.REKUEST_GRACE = {"DEFAULT": 30, "PER_MODE": {}, "PHYSICAL": 30}
        from asgiref.sync import async_to_sync

        from facade.models import Agent, Task

        ass = async_to_sync(build_task)("sweep-stale", effect="NONE")
        # Disconnected websocket executor, gone well past the grace window.
        Agent.objects.filter(pk=ass.agent_id).update(
            kind=enums.AgentKind.WEBSOCKET.value, connected=False, last_seen=timezone.now() - timedelta(minutes=5)
        )

        call_command("reconcile_tasks", stdout=StringIO())

        refreshed = Task.objects.get(pk=ass.pk)
        assert refreshed.latest_event_kind == enums.TaskEventKind.DISCONNECTED

    def test_sweep_leaves_connected_and_webhook_untouched(self, settings):
        settings.REKUEST_GRACE = {"DEFAULT": 30, "PER_MODE": {}, "PHYSICAL": 30}
        from asgiref.sync import async_to_sync

        from facade.models import Agent, Task

        connected = async_to_sync(build_task)("sweep-conn", effect="NONE")
        Agent.objects.filter(pk=connected.agent_id).update(
            kind=enums.AgentKind.WEBSOCKET.value, connected=True, last_seen=timezone.now()
        )
        webhook = async_to_sync(build_task)("sweep-hook", effect="NONE")
        Agent.objects.filter(pk=webhook.agent_id).update(
            kind=enums.AgentKind.WEBHOOK.value, connected=False, last_seen=timezone.now() - timedelta(minutes=5)
        )

        call_command("reconcile_tasks", stdout=StringIO())

        assert Task.objects.get(pk=connected.pk).latest_event_kind == enums.TaskEventKind.STARTED
        assert Task.objects.get(pk=webhook.pk).latest_event_kind == enums.TaskEventKind.STARTED
