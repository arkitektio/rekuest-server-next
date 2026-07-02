"""Single source of truth for "is this websocket agent alive?".

An agent's ``connected`` boolean is set True on connect/heartbeat and flipped False by the
disconnect handler — but that handler only runs on a clean socket close. A crashed/SIGKILLed
worker (or a half-open socket) never disconnects, so ``connected`` can stay stuck True with a
stale ``last_seen`` forever. Every liveness decision must therefore treat a connection as alive
only if it is BOTH ``connected`` AND has a recent heartbeat.

Historically each call site rolled its own staleness window (20 s / 1 min / 5 min); they are
unified here behind one ``AGENT_STALE_AFTER`` window so the reconnect gate, the availability
query, the GraphQL ``active`` field, and the healing reaper all agree.

This module is a LEAF: it imports only Django. ``agent_protocol`` cannot import ``backend``
(cycle ``backend → async_consumer → agent_protocol``), so the shared helper lives here where
both — and the models/types/management-command layers — can import it safely.
"""

from datetime import timedelta

from django.conf import settings
from django.db.models import Q
from django.utils import timezone


def stale_after_seconds() -> float:
    """Seconds without a heartbeat after which a ``connected`` agent is presumed dead.

    Defaults to 3× the heartbeat interval — comfortably above ``interval + response_timeout``,
    so a live agent (which refreshes ``last_seen`` every ``AGENT_HEARTBEAT_INTERVAL``) has to
    miss two full heartbeats before it is considered stale.
    """
    return float(getattr(settings, "AGENT_STALE_AFTER", 3 * settings.AGENT_HEARTBEAT_INTERVAL))


def agent_is_live(connected: bool, last_seen) -> bool:
    """Whether a websocket connection is genuinely alive: connected AND a fresh heartbeat."""
    if not connected or last_seen is None:
        return False
    return last_seen > timezone.now() - timedelta(seconds=stale_after_seconds())


def live_agent_q(prefix: str = "agent") -> Q:
    """Q matching a genuinely-live websocket agent (connected AND recently seen)."""
    p = f"{prefix}__" if prefix else ""
    return Q(**{f"{p}connected": True, f"{p}last_seen__gt": timezone.now() - timedelta(seconds=stale_after_seconds())})


def stale_agent_q(prefix: str = "agent") -> Q:
    """Q matching a stuck-connected agent: ``connected=True`` but the heartbeat expired (or was
    never recorded). These are exactly the rows the reaper heals back to ``connected=False``."""
    p = f"{prefix}__" if prefix else ""
    cutoff = timezone.now() - timedelta(seconds=stale_after_seconds())
    return Q(**{f"{p}connected": True}) & (Q(**{f"{p}last_seen__lt": cutoff}) | Q(**{f"{p}last_seen__isnull": True}))
