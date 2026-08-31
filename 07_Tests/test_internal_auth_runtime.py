from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / "06_Code"
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))

from kernel.internal_auth_runtime import issue_token, principal_from_headers, verify_token


def test_signed_session_round_trip_and_scope() -> None:
    key = "test-only-signing-key"
    token = issue_token(subject="naseem", role="founder", scopes=("hilm:manage",), ttl_seconds=600, now=1000, key=key)
    principal = verify_token(token, now=1100, key=key)
    assert principal.subject == "naseem"
    assert principal.role == "founder"
    assert principal.has_scope("hilm:manage")
    assert not principal.has_scope("trading:manage")


def test_same_token_verifies_offline_without_network() -> None:
    key = "offline-test-key"
    token = issue_token(subject="reception-1", role="reception", scopes=("hilm:pos",), ttl_seconds=3600, now=2000, key=key)
    principal = verify_token(token, now=2100, key=key)
    assert principal.role == "reception"
    assert principal.has_scope("hilm:pos")


def test_production_rejects_plain_role_header() -> None:
    try:
        principal_from_headers({"x-ameer-role": "founder"}, required_roles=("founder",), key="production-key", production=True)
    except ValueError as exc:
        assert str(exc) == "signed_internal_session_required"
    else:
        raise AssertionError("production accepted an unsigned role header")


def test_signed_session_enforces_role_and_scope() -> None:
    key = "production-key"
    token = issue_token(subject="cashier-1", role="reception", scopes=("hilm:pos",), ttl_seconds=600, now=3000, key=key)
    headers = {"authorization": f"Ameer {token}"}
    principal = principal_from_headers(headers, required_roles=("reception",), required_scope="hilm:pos", key=key, production=True)
    assert principal.subject == "cashier-1"

    try:
        principal_from_headers(headers, required_roles=("founder",), key=key, production=True)
    except PermissionError as exc:
        assert str(exc) == "role_not_authorized"
    else:
        raise AssertionError("role boundary was not enforced")


def test_tampered_token_is_rejected() -> None:
    key = "production-key"
    token = issue_token(subject="ameer", role="ameer", ttl_seconds=600, now=4000, key=key)
    body, signature = token.split(".", 1)
    tampered = f"{body}.{signature[:-1]}x"
    try:
        verify_token(tampered, now=4100, key=key)
    except ValueError as exc:
        assert str(exc) == "invalid_internal_token_signature"
    else:
        raise AssertionError("tampered token was accepted")
