"""DB-sweep safety net for orphaned executor work.

The in-memory grace timer is the *responsive* trigger for failing a lost executor's
in-flight work, but it is process-local: if the worker crashes (and the agent never
reconnects) the timer is gone and the work would stay ``is_done=False`` forever. This sweep
re-runs the same DB-authoritative reconcile op for any websocket executor that is
disconnected past the grace window — multi-worker-safe, idempotent. Run it on a schedule.

    python manage.py reconcile_assignations
"""

from __future__ import annotations

from datetime import timedelta

from asgiref.sync import async_to_sync
from django.core.management.base import BaseCommand
from django.utils import timezone

from facade import enums, models
from facade.grace import grace_seconds
from facade.messages import AgentMode
from facade.persist_backend import persist_backend


class Command(BaseCommand):
    help = "Fail orphaned in-flight work of websocket executors that are disconnected past the grace window."

    def handle(self, *args, **options) -> None:
        cutoff = timezone.now() - timedelta(seconds=grace_seconds(AgentMode.EXECUTOR))
        # Webhook agents never set connected/last_seen (no socket) — only sweep websocket
        # executors that are disconnected and have been gone longer than the grace window.
        agent_ids = list(
            models.Assignation.objects.filter(
                is_done=False,
                agent__kind=enums.AgentKind.WEBSOCKET.value,
                agent__connected=False,
                agent__last_seen__lt=cutoff,
            )
            .values_list("agent_id", flat=True)
            .distinct()
        )
        for agent_id in agent_ids:
            async_to_sync(persist_backend.reconcile_orphaned_executor_work)(agent_id)

        self.stdout.write(self.style.SUCCESS(f"reconcile_assignations: reconciled {len(agent_ids)} orphaned executor(s)."))
