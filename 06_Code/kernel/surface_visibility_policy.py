"""Server-side visibility rules for the Shadow System surfaces.

Public exposure is explicit. Unknown/future surfaces are private by default.
UI hiding alone is never treated as authorization.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import FrozenSet

PUBLIC_PREFIXES = (
    "/hilm/public",
    "/hilm/store",
    "/hilm/booking",
    "/hilm/services",
    "/hilm/prices",
    "/school/public",
)

PRIVATE_PREFIXES = (
    "/admin",
    "/trading",
    "/hilm/internal",
    "/hilm/management",
    "/hilm/pos",
    "/hilm/invoicing",
    "/hilm/operations",
    "/school/internal",
    "/ameer",
    "/ui/proactive",
)

ROLE_SCOPES = {
    "anonymous": frozenset({"public"}),
    "customer": frozenset({"public", "customer"}),
    "staff": frozenset({"public", "staff"}),
    "cashier": frozenset({"public", "staff", "cashier"}),
    "founder": frozenset({"public", "customer", "staff", "cashier", "private", "admin", "trading", "ameer"}),
    "ameer": frozenset({"public", "customer", "staff", "cashier", "private", "admin", "trading", "ameer"}),
}

@dataclass(frozen=True)
class AccessDecision:
    allowed: bool
    visibility: str
    reason: str


def classify_path(path: str) -> str:
    path = "/" + path.lstrip("/")
    if path in {"/health", "/"}:
        return "public"
    if any(path.startswith(prefix) for prefix in PUBLIC_PREFIXES):
        return "public"
    if any(path.startswith(prefix) for prefix in PRIVATE_PREFIXES):
        return "private"
    return "private"


def authorize_surface(path: str, role: str, *, staff_scopes: FrozenSet[str] = frozenset()) -> AccessDecision:
    visibility = classify_path(path)
    normalized = (role or "anonymous").strip().lower()
    scopes = ROLE_SCOPES.get(normalized, frozenset())
    if visibility == "public":
        return AccessDecision(True, visibility, "explicit_public_surface")
    if normalized in {"founder", "ameer"}:
        return AccessDecision(True, visibility, "founder_or_ameer_private_access")
    if normalized in {"staff", "cashier"}:
        required = "cashier" if path.startswith(("/hilm/pos", "/hilm/invoicing")) else "private"
        if required in staff_scopes or (normalized == "cashier" and required == "cashier"):
            return AccessDecision(True, visibility, "delegated_staff_scope")
        return AccessDecision(False, visibility, "staff_scope_missing")
    return AccessDecision(False, visibility, "private_surface")


def public_navigation() -> tuple[str, ...]:
    return ("hilm_public", "hilm_store", "school_public")
