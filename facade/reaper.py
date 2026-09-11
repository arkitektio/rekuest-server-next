"""Process-wide self-healing loop for stuck-connected agents.

The reconnect gate (``facade.liveness`` / ``AgentProtocol.on_register``) already lets a dead
agent take its slot back without ``--force``. But when NOBODY reconnects — a crashed/killed
worker whose ``disconnect()`` never ran — the agent's ``connected`` flag stays stuck True and
dashboards/GraphQL subscriptions keep reporting it alive. This loop is the responsive, no-cron
safety net that heals those rows (the ``reconcile_tasks`` management command is the equivalent
scheduled trigger over the same idempotent DB op).

Production runs under **daphne**, which does not implement the ASGI ``lifespan`` protocol, so
there is no startup hook to launch a background task from. Instead the loop is started lazily
and idempotently from :meth:`AgentConsumer.connect` — daphne runs everything on one asyncio
event loop, so the loop is live by the time any websocket connects (and if no agent ever
connects there is nothing to heal). One task per process; the reconcile op is idempotent, so
several daphne processes sweeping concurrently is safe.
"""

import asyncio
import logging
from typing import Optional

from channels.db import database_sync_to_async

from facade.liveness import stale_after_seconds
from facade.persist_backend import persist_backend
from facade.retention import sweep_terminal_tasks

logger = logging.getLogger(__name__)

_reaper_task: "Optional[asyncio.Task]" = None

# Retention runs on every Nth reaper tick: agent healing wants responsiveness, the
# retention horizon is measured in days — a slower cadence is plenty and keeps the
# common tick free of the sweep query.
_RETENTION_EVERY_N_TICKS = 10


def ensure_reaper_started() -> None:
    """Start the reaper loop once per process; a cheap no-op on every later call."""
    global _reaper_task
    if _reaper_task is not None and not _reaper_task.done():
        return
    _reaper_task = asyncio.ensure_future(_reaper_loop())


async def _reaper_loop() -> None:
    """Periodically heal stuck-connected agents; never let one bad iteration kill the loop."""
    tick = 0
    while True:
        try:
            await asyncio.sleep(stale_after_seconds())
            healed = await persist_backend.reconcile_stale_agents()
            if healed:
                logger.info("Reaper healed %s stuck-connected agent(s).", healed)
            tick += 1
            if tick % _RETENTION_EVERY_N_TICKS == 0:
                # One batch per slow tick; the scheduled reconcile_tasks command (or the
                # next tick) drains any backlog. No-op while retention is disabled.
                await database_sync_to_async(sweep_terminal_tasks)(max_batches=1)
        except asyncio.CancelledError:
            return
        except Exception:
            logger.error("Reaper iteration failed; continuing.", exc_info=True)
