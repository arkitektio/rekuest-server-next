"""Mint a signed provenance JWT for an assignment at dispatch.

Claim contract (one token per assignment, signed EdDSA / Ed25519). Standard
RFC-registered claims keep their canonical names for interoperability; Rekuest's
own claims use compact three-letter symbols (see docs/design/provenance.md for
the full vocabulary):

    iss          the Rekuest provenance issuer id                         (RFC 7519)
    aud          LIST of target services (declared/derived, never wildcard)(RFC 7519)
    sub          the immediate causer of THIS hop (request principal)      (RFC 7519)
    act.sub      the executing agent this token is issued to               (RFC 8693)
    act.cid      the executing agent's OAuth client_id
    iat / exp    issued-at / expiry                                        (RFC 7519)
    jti          unique per token (verifier enforces single-use)           (RFC 7519)
    tsk          this assignation id (task)
    ptk          parent assignation id (null if this is the root)
    rtk          root assignation id (== tsk when this is the root)
    rcb          root caused by — the human principal at the root (invariant: always human)
    ahs          args hash: sha256 of the canonicalized args (see canonical.py)
    aha          args hash algorithm/version, so verifiers know how to recompute
"""

from __future__ import annotations

import datetime
import logging
import uuid
from typing import Any, Dict, List, Optional

from django.conf import settings
from joserfc import jwt

from facade.provenance import canonical, keys, principal

logger = logging.getLogger(__name__)

# Guard against a pathological/corrupt parent cycle when walking to the root.
_MAX_LINEAGE_DEPTH = 256


def _resolve_root(assignation: Any) -> Any:
    """Walk the ``parent`` chain to the originating (root) assignation."""
    current = assignation
    seen = 0
    while current.parent_id is not None and seen < _MAX_LINEAGE_DEPTH:
        current = current.parent
        seen += 1
    return current


def _resolve_audience(implementation: Any) -> List[str]:
    """The token audience: the implementation's audience, resolved (declared or
    derived from its ports) at registration. Empty when it touches no external service."""
    return list(implementation.provenance_audience or [])


def _current_roles(info: Any) -> List[str]:
    """Roles of the principal making the current request (best effort)."""
    try:
        return list(info.context.request.membership.roles or [])
    except Exception:
        return []


def _sign(claims: Dict[str, Any]) -> str:
    header = {"alg": keys.ALGORITHM, "kid": settings.PROVENANCE["KID"], "typ": "JWT"}
    return jwt.encode(header, claims, keys.get_signing_key(), algorithms=keys.ALGORITHMS)


def mint_token_for_assignation(assignation: Any, info: Any) -> Optional[str]:
    """Mint the provenance token for ``assignation``, or return None to skip.

    Returns None when the implementation opts out (``needs_token=False``) or when
    the root principal cannot be confirmed human under a lenient policy. Raises
    ``ValueError`` for a non-human root under a strict policy.
    """
    implementation = assignation.implementation
    if implementation is None or not implementation.needs_token:
        return None

    agent = assignation.agent
    request = info.context.request

    is_top = assignation.parent_id is None
    root = assignation if is_top else _resolve_root(assignation)

    # Immediate causer of this hop, and the human at the root of the tree.
    sub = str(request.user.sub)
    if is_top:
        root_caused_by = sub
        root_human = principal.is_human_by_roles(_current_roles(info))
    else:
        root_caller = root.caller
        if root_caller is None or root_caller.user_id is None:
            root_caused_by = None
            root_human = False
        else:
            root_caused_by = str(root_caller.user.sub)
            root_human = principal.is_human_caller(root_caller)

    if not root_human:
        message = (
            f"Refusing to mint provenance token for assignation {assignation.pk}: "
            f"root principal (root_caused_by={root_caused_by}) is not an accountable human."
        )
        if settings.PROVENANCE["STRICT"]:
            raise ValueError(message)
        logger.warning(message)
        return None

    now = datetime.datetime.now(datetime.timezone.utc)
    exp = now + datetime.timedelta(seconds=settings.PROVENANCE["TOKEN_TTL_SECONDS"])

    claims: Dict[str, Any] = {
        # RFC-registered claims keep their canonical names for interop.
        "iss": keys.issuer(),
        "aud": _resolve_audience(implementation),
        "sub": sub,
        "act": {"sub": str(agent.user.sub), "cid": str(agent.client.client_id)},
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "jti": str(uuid.uuid4()),
        # Rekuest provenance claims (compact symbols; see docs/design/provenance.md).
        "tsk": str(assignation.pk),
        "ptk": str(assignation.parent_id) if assignation.parent_id else None,
        "rtk": str(root.pk),
        "rcb": root_caused_by,
        "ahs": canonical.args_hash(assignation.args or {}),
        "aha": f"sha256-canonical-v{canonical.CANONICALIZATION_VERSION}",
    }

    return _sign(claims)
