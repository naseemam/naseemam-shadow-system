"""
credential_sanitizer.py
========================
Centralized credential sanitizer for Ameer.

Strips sensitive values (API keys, tokens, passwords, secrets, ******
Authorization headers, and credential-like values) from any dict/list payload
before it reaches logs, .ameer persistence, response payloads, or execution records.

Usage
-----
from kernel.credential_sanitizer import sanitize

safe = sanitize(payload)          # works on dict, list, or str
"""

from __future__ import annotations

import re
from typing import Any

# ── Sensitive key patterns (case-insensitive substring match) ─────────────────

_SENSITIVE_KEYS: tuple[str, ...] = (
    "api_key",
    "apikey",
    "token",
    "password",
    "passwd",
    "secret",
    "authorization",
    "bearer",
    "credential",
    "credentials",
    "private_key",
    "privatekey",
    "access_key",
    "accesskey",
    "client_secret",
    "client_id",
    "refresh_token",
    "id_token",
    "jwt",
    "session_token",
    "x-api-key",
    "x-auth-token",
    "x-secret",
)

# ── Patterns that look like credential values regardless of key name ──────────

_CREDENTIAL_VALUE_PATTERNS: list[re.Pattern] = [
    # ****** Basic tokens in header values
    re.compile(r"\bbearer\s+[A-Za-z0-9\-._~+/]+=*", re.IGNORECASE),
    re.compile(r"\bbasic\s+[A-Za-z0-9+/]+=*", re.IGNORECASE),
    # OpenAI / Anthropic / generic sk- tokens
    re.compile(r"\bsk-[A-Za-z0-9]{16,}", re.IGNORECASE),
    # GitHub PAT-style tokens
    re.compile(r"\bghp_[A-Za-z0-9]{36,}", re.IGNORECASE),
    re.compile(r"\bghs_[A-Za-z0-9]{36,}", re.IGNORECASE),
    re.compile(r"\bgho_[A-Za-z0-9]{36,}", re.IGNORECASE),
    # AWS keys
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    # Generic long hex/base64 that look like secrets (32+ chars, no whitespace)
    re.compile(r"\b[A-Fa-f0-9]{32,}\b"),
]

_REDACTED = "[REDACTED]"


def _is_sensitive_key(key: str) -> bool:
    key_lower = str(key).lower().replace("-", "_").replace(" ", "_")
    return any(pattern in key_lower for pattern in _SENSITIVE_KEYS)


def _sanitize_string(value: str) -> str:
    """Redact credential-like patterns found inside a string value."""
    for pattern in _CREDENTIAL_VALUE_PATTERNS:
        value = pattern.sub(_REDACTED, value)
    return value


def sanitize(payload: Any, *, _depth: int = 0) -> Any:
    """
    Recursively sanitize *payload*, redacting credential-like content.

    - dict keys that match _SENSITIVE_KEYS → value replaced with _REDACTED
    - string values → credential-like patterns replaced with _REDACTED
    - lists and tuples → each element recursively sanitized
    - all other types returned as-is

    The recursion depth is capped at 20 to prevent pathological inputs.
    """
    if _depth > 20:
        return payload

    if isinstance(payload, dict):
        clean: dict[str, Any] = {}
        for k, v in payload.items():
            if _is_sensitive_key(k):
                clean[k] = _REDACTED
            else:
                clean[k] = sanitize(v, _depth=_depth + 1)
        return clean

    if isinstance(payload, list):
        return [sanitize(item, _depth=_depth + 1) for item in payload]

    if isinstance(payload, tuple):
        return tuple(sanitize(item, _depth=_depth + 1) for item in payload)

    if isinstance(payload, str):
        return _sanitize_string(payload)

    return payload
