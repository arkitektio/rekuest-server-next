"""Provenance token issuing.

Rekuest is the *provenance authority*: at dispatch it mints a signed (Ed25519)
JWT attesting who caused an assignment and with which inputs, and
publishes the verifying key at a JWKS endpoint. This is an attestation meant to
be recorded downstream (e.g. by Mikro/koherent), never an authorization grant —
it is orthogonal to the auth JWT that gates writes.

Verification, single-use ``jti`` enforcement, actor-binding and the provenance
store all live downstream and are intentionally *not* implemented here. Rekuest's
job ends at emitting a correct, signed, conformant claim set.
"""

from facade.provenance.mint import mint_token_for_task

__all__ = ["mint_token_for_task"]
