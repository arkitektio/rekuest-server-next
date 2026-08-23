"""Single source of truth for "is this websocket agent alive?".

Liveness is read as ``connected AND a fresh heartbeat``, and the asymmetry is deliberate:

* ``connected=False`` is a **definitive negative** — somebody observed a clean close (or the
  sweep revoked the lease), so the agent is instantly, correctly not-live.
* ``connected=True`` is only **not-yet-refuted**. It is written on connect and flipped by the
  disconnect handler, which runs only on a clean close — a crashed/SIGKILLed worker never
  disconnects, so the flag can stay stuck True forever. The heartbeat lease (``last_seen``) is
  what makes True trustworthy: it expires on its own, with no writer.

So the *read* predicate needs no repair; correctness lives in the **write discipline** on the
other side (``facade.persist_backend``):

* **Transitions** — claim (connect), release (disconnect), revoke (sweep) — take a row lock
  (``select_for_update``) and go through ``Model.save()`` so ``agent_post_save`` fires and the
  GraphQL agent feeds see the change.
* **Renewal** — the heartbeat, the only hot path (once per ``AGENT_HEARTBEAT_INTERVAL`` per
  agent) — is a lock-free compare-and-set on ``lease_epoch``; its rowcount *is* the answer to
  "am I still the owner?". A displaced or revoked connection matches no row and closes itself.

Every socket connection is an agent and holds that agent's lease, so every heartbeat renews.
(There used to be caller/observer connection modes sharing the same ``Agent`` row — identity is
``client``/``user``/``organization`` — whose heartbeats touched ``last_seen`` and let an open
dashboard forge executor liveness indefinitely. Those modes are gone: users originate work only
through the GraphQL ``assign`` mutation.)

Note on stuck flags: the heartbeat ping/pong already closes half-open sockets (no answer within
``AGENT_HEARTBEAT_RESPONSE_TIMEOUT`` → ``HEARTBEAT_NOT_RESPONDED_CODE``). The residual causes of
a stuck ``connected=True`` are **displacement** and **hard worker death** — which is why the
fix is a fencing token plus a sweep, not a longer timeout.

All liveness timestamps are written with the *application* clock (``timezone.now()``) and
compared against it, so the whole predicate lives in one clock domain and only needs the app
servers to be NTP-synced. Do not mix in the database clock (``Now()``): that would add an
app-vs-DB skew axis on top of the app-vs-app one.

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


def agent_is_stale(connected: bool, last_seen) -> bool:
    """Whether an agent is stuck-connected: ``connected`` but its lease expired (or never began).

    The in-Python twin of :func:`stale_agent_q` — exactly the rows the sweep revokes. Note this
    is NOT ``not agent_is_live(...)``: a cleanly disconnected agent is neither live nor stale,
    because there is nothing left to heal.
    """
    return bool(connected) and not agent_is_live(connected, last_seen)


def live_agent_q(prefix: str = "agent") -> Q:
    """Q matching a genuinely-live websocket agent (connected AND recently seen)."""
    p = f"{prefix}__" if prefix else ""
    return Q(**{f"{p}connected": True, f"{p}last_seen__gt": timezone.now() - timedelta(seconds=stale_after_seconds())})


def stale_agent_q(prefix: str = "agent") -> Q:
    """Q matching a stuck-connected agent: ``connected=True`` but the heartbeat expired (or was
    never recorded). These are exactly the rows the reaper revokes back to ``connected=False``."""
    p = f"{prefix}__" if prefix else ""
    cutoff = timezone.now() - timedelta(seconds=stale_after_seconds())
    return Q(**{f"{p}connected": True}) & (Q(**{f"{p}last_seen__lt": cutoff}) | Q(**{f"{p}last_seen__isnull": True}))
