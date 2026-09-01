"""Signed internal authentication for Ameer private operational APIs.

Production must use HMAC-signed bearer sessions. Local/offline clients can verify
exactly the same token without network access. Legacy role headers are accepted
only outside production while old internal tests and development tools migrate.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from dataclasses import dataclass
from typing import Iterable, Mapping, Optional


AUTH_KEY_ENV = "AMEER_INTERNAL_AUTH_KEY"
AUTH_MODE_ENV = "AMEER_AUTH_MODE"
LEGACY_HEADER = "x-ameer-role"
TOKEN_PREFIX = "Ameer "


def _b64e(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64d(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode((value + padding).encode("ascii"))


def _key(explicit: Optional[str] = None) -> bytes:
    value = explicit if explicit is not None else os.getenv(AUTH_KEY_ENV, "")
    if not value:
        raise ValueError("internal_auth_key_missing")
    return value.encode("utf-8")


@dataclass(frozen=True)
class InternalPrincipal:
    subject: str
    role: str
    scopes: tuple[str, ...]
    issued_at: int
    expires_at: int
    auth_kind: str = "signed_session"

    def has_scope(self, required: str) -> bool:
        return "*" in self.scopes or required in self.scopes


def issue_token(*, subject: str, role: str, scopes: Iterable[str] = ("*",), ttl_seconds: int = 3600, now: Optional[int] = None, key: Optional[str] = None) -> str:
    if ttl_seconds <= 0:
        raise ValueError("ttl_must_be_positive")
    issued = int(time.time() if now is None else now)
    payload = {
        "sub": str(subject),
        "role": str(role).strip().lower(),
        "scopes": sorted({str(scope) for scope in scopes}),
        "iat": issued,
        "exp": issued + int(ttl_seconds),
        "v": 1,
    }
    body = _b64e(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    signature = _b64e(hmac.new(_key(key), body.encode("ascii"), hashlib.sha256).digest())
    return f"{body}.{signature}"


def verify_token(token: str, *, now: Optional[int] = None, key: Optional[str] = None) -> InternalPrincipal:
    try:
        body, supplied_signature = token.split(".", 1)
    except ValueError as exc:
        raise ValueError("invalid_internal_token") from exc
    expected = _b64e(hmac.new(_key(key), body.encode("ascii"), hashlib.sha256).digest())
    if not hmac.compare_digest(expected, supplied_signature):
        raise ValueError("invalid_internal_token_signature")
    try:
        payload = json.loads(_b64d(body).decode("utf-8"))
    except Exception as exc:
        raise ValueError("invalid_internal_token_payload") from exc
    current = int(time.time() if now is None else now)
    if int(payload.get("exp") or 0) <= current:
        raise ValueError("internal_token_expired")
    if int(payload.get("iat") or 0) > current + 60:
        raise ValueError("internal_token_issued_in_future")
    subject = str(payload.get("sub") or "").strip()
    role = str(payload.get("role") or "").strip().lower()
    scopes = tuple(str(scope) for scope in payload.get("scopes") or ())
    if not subject or not role:
        raise ValueError("internal_token_identity_missing")
    return InternalPrincipal(subject=subject, role=role, scopes=scopes, issued_at=int(payload["iat"]), expires_at=int(payload["exp"]))


def principal_from_headers(headers: Mapping[str, str], *, required_roles: Iterable[str] = (), required_scope: str = "", key: Optional[str] = None, production: Optional[bool] = None) -> InternalPrincipal:
    is_production = (os.getenv(AUTH_MODE_ENV, "").strip().lower() == "production") if production is None else bool(production)
    authorization = str(headers.get("authorization") or "").strip()
    secret_available = bool(key if key is not None else os.getenv(AUTH_KEY_ENV, ""))

    if authorization.startswith(TOKEN_PREFIX):
        principal = verify_token(authorization[len(TOKEN_PREFIX):].strip(), key=key)
    elif is_production or secret_available:
        raise ValueError("signed_internal_session_required")
    else:
        # Temporary migration path for private development only. Production never
        # trusts this header and a configured signing key automatically disables it.
        role = str(headers.get(LEGACY_HEADER) or "").strip().lower()
        if not role:
            raise ValueError("internal_identity_required")
        principal = InternalPrincipal(subject=f"legacy:{role}", role=role, scopes=("*",), issued_at=0, expires_at=2**31 - 1, auth_kind="legacy_development_header")

    allowed = {str(role).strip().lower() for role in required_roles}
    if allowed and principal.role not in allowed:
        raise PermissionError("role_not_authorized")
    if required_scope and not principal.has_scope(required_scope):
        raise PermissionError("scope_not_authorized")
    return principal
