"""Resolve the per-mode reclaim grace window.

On a disconnect the failure/cascade is delayed by a grace window so a brief blip can
reclaim same-session in-flight work before it fires (see the reclaim/grace backend). The
window is configured by the ``REKUEST_GRACE`` setting and resolved here so both the
executor-death and caller-death paths read it the same way.
"""

from __future__ import annotations

import asyncio
from typing import Awaitable, Callable, Dict, Optional

from django.conf import settings

from facade.messages import AgentMode

ReconcileAction = Callable[[], Awaitable[None]]


class GraceScheduler:
    """A keyed set of single-shot delayed tasks — the *responsive* reconcile trigger.

    ``schedule(key, delay, action)`` runs ``action`` after ``delay`` unless ``cancel(key)``
    is called first (a reconnect). It is just a trigger: ``action`` is an idempotent DB
    reconcile op (the WHAT), so the DB stays authoritative whether the trigger is this timer,
    a reconnect, or the periodic sweep. Keys are normalized to ``str`` so int pks and string
    session/connection ids interoperate. Supports ``in`` / ``[]`` for introspection + tests.
    """

    def __init__(self) -> None:
        self._tasks: Dict[str, asyncio.Task] = {}

    def schedule(self, key: object, delay: float, action: ReconcileAction) -> None:
        skey = str(key)
        self.cancel(skey)
        self._tasks[skey] = asyncio.create_task(self._run(skey, delay, action))

    def cancel(self, key: object) -> None:
        if key is None:
            return
        task = self._tasks.pop(str(key), None)
        if task is not None and not task.done():
            task.cancel()

    async def _run(self, key: str, delay: float, action: ReconcileAction) -> None:
        try:
            await asyncio.sleep(delay)
        except asyncio.CancelledError:
            return  # reclaimed — a reconnect / terminal cancelled us
        try:
            await action()
        finally:
            self._tasks.pop(key, None)

    def __contains__(self, key: object) -> bool:
        return str(key) in self._tasks

    def __getitem__(self, key: object) -> asyncio.Task:
        return self._tasks[str(key)]

    def get(self, key: object) -> Optional[asyncio.Task]:
        return self._tasks.get(str(key))


def grace_seconds(mode: AgentMode | str | None = None, *, physical: bool = False) -> float:
    """Grace window (seconds) for ``mode``; ``physical`` overrides for effect:physical work.

    Resolution order: explicit ``PHYSICAL`` override (when ``physical``) → per-mode override
    → ``DEFAULT``. 0 means no grace (strict). Returned as a float so sub-second windows
    (e.g. in tests) are not truncated to 0.

    NOTE: no call site currently passes ``physical=`` — effect-awareness lives in the
    fail/reclaim branching of ``persist_backend``, not in the grace timer.
    """
    cfg = getattr(settings, "REKUEST_GRACE", {}) or {}

    if physical and cfg.get("PHYSICAL") is not None:
        return float(cfg["PHYSICAL"])

    if mode is not None:
        key = AgentMode(mode).value
        per_mode = cfg.get("PER_MODE", {}) or {}
        if key in per_mode:
            return float(per_mode[key])

    return float(cfg.get("DEFAULT", 0))


def progress_lease_seconds() -> float:
    """The progress-lease window (seconds); 0 disables the lease."""
    cfg = getattr(settings, "REKUEST_GRACE", {}) or {}
    return float(cfg.get("PROGRESS_LEASE", 0))
