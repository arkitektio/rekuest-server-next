"""Ed25519 signing key + JWKS document for the provenance issuer.

The private key is loaded from ``settings.PROVENANCE`` (sourced from the
``provenance`` block of config.yaml, mirroring how ``lok`` keys are provided).
If no key is configured an ephemeral keypair is generated once per process and a
warning is logged — this keeps dispatch and the local test-suite working out of
the box, but is unsuitable for multi-replica production (replicas would each sign
under a different key). Configure a static key in production.
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Dict

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
from django.conf import settings
from joserfc.jwk import OKPKey

logger = logging.getLogger(__name__)

# RFC 9864 fully-specified algorithm identifier for Ed25519 JWS. This replaces
# the now-deprecated generic "EdDSA" identifier (RFC 8037), which joserfc flags
# with a SecurityWarning. It must be passed explicitly wherever we sign/verify.
ALGORITHM = "Ed25519"
ALGORITHMS = [ALGORITHM]

_lock = threading.Lock()
_signing_key: OKPKey | None = None
_public_key: OKPKey | None = None


def _kid() -> str:
    return settings.PROVENANCE["KID"]


def issuer() -> str:
    """The configured provenance issuer id (the token ``iss`` claim)."""
    return settings.PROVENANCE["ISSUER"]


def _generate_ephemeral_pems() -> tuple[bytes, bytes]:
    key = ed25519.Ed25519PrivateKey.generate()
    private_pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    public_pem = key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return private_pem, public_pem


def _load() -> None:
    """Populate the module-level signing/public keys (idempotent, thread-safe)."""
    global _signing_key, _public_key
    if _signing_key is not None:
        return

    with _lock:
        if _signing_key is not None:
            return

        conf = settings.PROVENANCE
        private_pem = conf.get("PRIVATE_KEY")
        public_pem = conf.get("PUBLIC_KEY")

        if not private_pem:
            logger.warning(
                "No provenance private key configured (settings.PROVENANCE['PRIVATE_KEY']); "
                "generating an ephemeral Ed25519 keypair. Tokens will not verify across "
                "process restarts or replicas — configure a static key for production."
            )
            private_pem, public_pem = _generate_ephemeral_pems()

        kid = _kid()
        signing = OKPKey.import_key(private_pem, {"kid": kid})
        if public_pem:
            public = OKPKey.import_key(public_pem, {"kid": kid})
        else:
            # Derive the public JWK from the private key.
            public = OKPKey.import_key(
                signing.public_key.public_bytes(
                    serialization.Encoding.PEM,
                    serialization.PublicFormat.SubjectPublicKeyInfo,
                ),
                {"kid": kid},
            )

        _signing_key = signing
        _public_key = public


def get_signing_key() -> OKPKey:
    """The Ed25519 private key used to sign provenance tokens."""
    _load()
    assert _signing_key is not None
    return _signing_key


def get_public_key() -> OKPKey:
    """The Ed25519 public key used to verify provenance tokens."""
    _load()
    assert _public_key is not None
    return _public_key


def get_public_jwk() -> Dict[str, Any]:
    """The public key as a JWK dict, with ``kid``/``use``/``alg`` set."""
    jwk = get_public_key().as_dict(kid=_kid())
    jwk.setdefault("use", "sig")
    jwk.setdefault("alg", ALGORITHM)
    return jwk


def get_jwks_document() -> Dict[str, Any]:
    """The JWKS document published at the JWKS endpoint for offline verification."""
    return {"keys": [get_public_jwk()]}


def reset_cache() -> None:
    """Drop the cached keys so a subsequent call reloads from settings (tests)."""
    global _signing_key, _public_key
    with _lock:
        _signing_key = None
        _public_key = None
