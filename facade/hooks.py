"""HTTP-POST transport for HookAgents (``Agent.kind == WEBHOOK``).

A HookAgent speaks the same message protocol as a websocket agent, but over HTTP: the
backend POSTs downstream messages to ``agent.hook_url`` and the agent POSTs upstream
messages to the intake endpoint. Both directions are authenticated by an HMAC over the
shared ``agent.hook_url_secret`` — there is no JWT on the HTTP path.

Delivery is persist-then-POST: callers persist the Assignation/event row *before* calling
out here, so a failed POST is logged (not raised) and the persisted row remains the durable
record from which a later redelivery sweep can re-POST.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
from typing import TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    from facade import models

logger = logging.getLogger(__name__)

SIGNATURE_HEADER = "X-Rekuest-Signature"
_TIMEOUT = 10.0

# Module-level client: connection pooling across many deliveries.
_client = httpx.Client(timeout=_TIMEOUT)


def sign(secret: str, body: bytes) -> str:
    """HMAC-SHA256 hex digest of ``body`` under ``secret``."""
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


def verify(secret: str | None, body: bytes, signature: str | None) -> bool:
    """Constant-time check that ``signature`` is a valid HMAC of ``body`` under ``secret``."""
    if not secret or not signature:
        return False
    return hmac.compare_digest(sign(secret, body), signature)


def deliver_to_hook(agent: "models.Agent", body: str) -> bool:
    """POST ``body`` (a JSON message) to ``agent.hook_url``, HMAC-signed. Never raises.

    Returns True on a 2xx response. Failures are logged — the persisted Assignation/event
    row is the durable record, so a failed delivery is recoverable, not lost.
    """
    url = getattr(agent, "hook_url", None)
    if not url:
        logger.error("HookAgent %s has no hook_url; dropping message", getattr(agent, "pk", "?"))
        return False

    raw = body.encode("utf-8")
    headers = {"Content-Type": "application/json"}
    secret = getattr(agent, "hook_url_secret", None)
    if secret:
        headers[SIGNATURE_HEADER] = sign(secret, raw)

    try:
        response = _client.post(url, content=raw, headers=headers)
        response.raise_for_status()
        return True
    except Exception:
        logger.error("Failed to deliver message to HookAgent %s at %s", getattr(agent, "pk", "?"), url, exc_info=True)
        return False
