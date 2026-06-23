"""Tests for the provenance token issuing side.

These exercise Rekuest's role as the provenance *issuer*: key/JWKS publication,
the canonical args hash, audience resolution, the human-root invariant, and the
shape + signature of the minted claim set. Verification semantics that belong
downstream (single-use jti, actor binding, args_hash recomputation) are out of
scope here.

The mint tests use lightweight fakes for the task/request graph so the
issuing logic can be verified without standing up the database — the claim
contract depends only on attributes Rekuest reads off those objects.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Optional

import pytest
from django.conf import settings
from joserfc import jwt
from joserfc.jwk import KeySet

from facade.provenance import audience, canonical, keys, mint, principal


def _decode(token: Optional[str]) -> Any:
    """Verify + decode a minted token against the published public key."""
    assert token is not None, "expected a minted token, got None"
    key_set = KeySet([keys.get_public_key()])
    return jwt.decode(token, key_set, algorithms=keys.ALGORITHMS)


def _agent(user_sub: str = "agent-sub", client_id: str = "agent-client") -> Any:
    return SimpleNamespace(user=SimpleNamespace(sub=user_sub), client=SimpleNamespace(client_id=client_id))


def _implementation(needs_token: bool = True, provenance_audience: Optional[list[str]] = None) -> Any:
    return SimpleNamespace(needs_token=needs_token, provenance_audience=provenance_audience)


def _task(
    pk: str,
    *,
    implementation: Any = None,
    agent: Any = None,
    args: Optional[dict] = None,
    acted_on: Optional[list[str]] = None,
    parent: Any = None,
    caller: Any = None,
) -> Any:
    return SimpleNamespace(
        pk=pk,
        implementation=implementation if implementation is not None else _implementation(),
        agent=agent if agent is not None else _agent(),
        args=args or {},
        acted_on=acted_on or [],
        parent=parent,
        parent_id=parent.pk if parent is not None else None,
        caller=caller,
    )


def _info(user_sub: str = "human-sub", roles: Optional[list[str]] = None) -> Any:
    request = SimpleNamespace(
        user=SimpleNamespace(sub=user_sub),
        membership=SimpleNamespace(roles=roles or []),
    )
    return SimpleNamespace(context=SimpleNamespace(request=request))


@pytest.fixture
def lenient(monkeypatch: pytest.MonkeyPatch) -> None:
    """Default provenance policy: human-root enforcement off, no default audience."""
    monkeypatch.setitem(settings.PROVENANCE, "HUMAN_ROLES", [])
    monkeypatch.setitem(settings.PROVENANCE, "STRICT", False)
    monkeypatch.setitem(settings.PROVENANCE, "DEFAULT_AUDIENCE", [])


# --- canonical args hash -------------------------------------------------


def test_args_hash_is_order_independent() -> None:
    assert canonical.args_hash({"a": 1, "b": 2}) == canonical.args_hash({"b": 2, "a": 1})


def test_args_hash_differs_on_different_args() -> None:
    assert canonical.args_hash({"a": 1}) != canonical.args_hash({"a": 2})


def test_args_hash_empty_is_stable() -> None:
    assert canonical.args_hash({}) == canonical.args_hash(None or {})


# --- JWKS / keys ---------------------------------------------------------


def test_jwks_endpoint_serves_cacheable_document() -> None:
    from django.test import RequestFactory

    from rekuest.urls import jwks_view

    response = jwks_view(RequestFactory().get("/.well-known/jwks.json"))
    assert response.status_code == 200
    assert "public" in response["Cache-Control"]
    import json

    doc = json.loads(response.content)
    assert doc["keys"][0]["kid"] == settings.PROVENANCE["KID"]


def test_jwks_document_publishes_signing_key() -> None:
    doc = keys.get_jwks_document()
    assert "keys" in doc and len(doc["keys"]) == 1
    jwk = doc["keys"][0]
    assert jwk["kty"] == "OKP"
    assert jwk["crv"] == "Ed25519"
    assert jwk["kid"] == settings.PROVENANCE["KID"]
    assert jwk["alg"] == "EdDSA"
    assert jwk["use"] == "sig"
    # The published key is public only — no private component.
    assert "d" not in jwk


# --- audience derivation (registration time) -----------------------------


def test_services_from_ports_extracts_and_dedupes() -> None:
    args = [{"kind": "STRUCTURE", "identifier": "@mikro/image"}, {"kind": "INT"}]
    returns = [
        {"kind": "STRUCTURE", "identifier": "@mikro/roi"},
        {"kind": "STRUCTURE", "identifier": "@fluss/flow"},
    ]
    assert audience.services_from_ports(args, returns) == ["mikro", "fluss"]


def test_services_from_ports_walks_nested_children() -> None:
    args = [{"kind": "LIST", "children": [{"kind": "STRUCTURE", "identifier": "@mikro/image"}]}]
    assert audience.services_from_ports(args) == ["mikro"]


def test_derive_from_action_uses_args_and_returns() -> None:
    action = SimpleNamespace(
        args=[{"kind": "STRUCTURE", "identifier": "@mikro/image"}],
        returns=[{"kind": "STRUCTURE", "identifier": "@fluss/flow"}],
    )
    assert audience.derive_from_action(action) == ["mikro", "fluss"]


# --- audience on the token (read from the implementation) -----------------


def test_audience_taken_from_implementation(lenient: None) -> None:
    impl = _implementation(provenance_audience=["mikro", "fluss"])
    task = _task("1", implementation=impl)
    token = mint.mint_token_for_task(task, _info())
    assert _decode(token).claims["aud"] == ["mikro", "fluss"]


def test_audience_empty_when_implementation_has_none(lenient: None) -> None:
    task = _task("1", implementation=_implementation(provenance_audience=None))
    token = mint.mint_token_for_task(task, _info())
    assert _decode(token).claims["aud"] == []


# --- needs_token ---------------------------------------------------------


def test_needs_token_false_skips_minting(lenient: None) -> None:
    impl = _implementation(needs_token=False)
    task = _task("1", implementation=impl)
    assert mint.mint_token_for_task(task, _info()) is None


# --- top-level claim correctness -----------------------------------------


def test_top_level_claims(lenient: None) -> None:
    agent = _agent(user_sub="agent-9", client_id="client-9")
    impl = _implementation(provenance_audience=["mikro"])
    task = _task("assign-1", implementation=impl, agent=agent, args={"x": 1})
    info = _info(user_sub="human-7")

    token = mint.mint_token_for_task(task, info)
    decoded = _decode(token)

    # Header: pinned EdDSA, kid present.
    assert decoded.header["alg"] == "EdDSA"
    assert decoded.header["kid"] == settings.PROVENANCE["KID"]

    claims = decoded.claims
    assert claims["iss"] == settings.PROVENANCE["ISSUER"]
    assert claims["aud"] == ["mikro"]
    # Top-level: immediate cause and root human coincide; root is self.
    assert claims["sub"] == "human-7"
    assert claims["rcb"] == "human-7"
    assert claims["tsk"] == "assign-1"
    assert claims["rtk"] == "assign-1"
    assert claims["ptk"] is None
    # Actor: the executing agent this token is issued to.
    assert claims["act"] == {"sub": "agent-9", "cid": "client-9"}
    # Args bound by hash, with a versioned algorithm tag.
    assert claims["ahs"] == canonical.args_hash({"x": 1})
    assert claims["aha"] == f"sha256-canonical-v{canonical.CANONICALIZATION_VERSION}"
    assert "jti" in claims and "iat" in claims and "exp" in claims
    assert claims["exp"] > claims["iat"]


def test_jti_is_unique_per_mint(lenient: None) -> None:
    task = _task("1")
    info = _info()
    jtis = {_decode(mint.mint_token_for_task(task, info)).claims["jti"] for _ in range(5)}
    assert len(jtis) == 5


# --- sub-assignment lineage inheritance ----------------------------------


def test_sub_assignment_inherits_root(lenient: None) -> None:
    root_caller = SimpleNamespace(user=SimpleNamespace(sub="root-human"), user_id=1, organization_id=1)
    root = _task("root-1", caller=root_caller)
    child = _task("child-1", parent=root)
    # The hop is caused by some service principal, not the root human.
    info = _info(user_sub="service-principal")

    token = mint.mint_token_for_task(child, info)
    claims = _decode(token).claims

    assert claims["tsk"] == "child-1"
    assert claims["ptk"] == "root-1"
    assert claims["rtk"] == "root-1"
    # Root human inherited from the root task's caller, not the hop principal.
    assert claims["rcb"] == "root-human"
    assert claims["sub"] == "service-principal"


# --- human-root invariant ------------------------------------------------


def test_strict_refuses_non_human_root(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(settings.PROVENANCE, "HUMAN_ROLES", ["user"])
    monkeypatch.setitem(settings.PROVENANCE, "STRICT", True)
    task = _task("1")
    info = _info(roles=["service"])  # no "user" role
    with pytest.raises(ValueError):
        mint.mint_token_for_task(task, info)


def test_lenient_skips_non_human_root(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(settings.PROVENANCE, "HUMAN_ROLES", ["user"])
    monkeypatch.setitem(settings.PROVENANCE, "STRICT", False)
    task = _task("1")
    info = _info(roles=["service"])
    assert mint.mint_token_for_task(task, info) is None


def test_human_role_allows_mint(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(settings.PROVENANCE, "HUMAN_ROLES", ["user"])
    monkeypatch.setitem(settings.PROVENANCE, "STRICT", True)
    monkeypatch.setitem(settings.PROVENANCE, "DEFAULT_AUDIENCE", [])
    task = _task("1")
    info = _info(user_sub="real-human", roles=["user", "viewer"])
    token = mint.mint_token_for_task(task, info)
    assert _decode(token).claims["rcb"] == "real-human"


# --- predicate unit ------------------------------------------------------


def test_is_human_by_roles_lenient_when_unconfigured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(settings.PROVENANCE, "HUMAN_ROLES", [])
    assert principal.is_human_by_roles([]) is True


def test_is_human_by_roles_requires_match_when_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(settings.PROVENANCE, "HUMAN_ROLES", ["user"])
    assert principal.is_human_by_roles(["service"]) is False
    assert principal.is_human_by_roles(["user"]) is True
