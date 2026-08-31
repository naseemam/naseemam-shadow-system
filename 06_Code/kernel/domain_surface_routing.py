"""Canonical host/surface routing for AmeerNas public and private zones.

This module prepares routing policy only. DNS cutover remains a separate sovereign action.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


MOTHER_HOST = "ameernas.com"
HILM_PUBLIC_HOST = "hilm.ameernas.com"
SCHOOL_PUBLIC_HOST = "school.ameernas.com"


@dataclass(frozen=True)
class SurfaceRoute:
    host: str
    surface: str
    visibility: str
    requires_auth: bool


ROUTES: Dict[str, SurfaceRoute] = {
    MOTHER_HOST: SurfaceRoute(MOTHER_HOST, "mother_private", "private", True),
    HILM_PUBLIC_HOST: SurfaceRoute(HILM_PUBLIC_HOST, "hilm_public", "public", False),
    SCHOOL_PUBLIC_HOST: SurfaceRoute(SCHOOL_PUBLIC_HOST, "school_public", "public", False),
}


def normalize_host(host: str) -> str:
    value = (host or "").strip().lower().split(":", 1)[0].rstrip(".")
    if value.startswith("www."):
        value = value[4:]
    return value


def route_for_host(host: str) -> SurfaceRoute:
    """Fail closed: unknown hosts never become public by accident."""
    normalized = normalize_host(host)
    return ROUTES.get(normalized, SurfaceRoute(normalized, "unknown_private", "private", True))


def public_host(host: str) -> bool:
    return route_for_host(host).visibility == "public"


def deployment_readiness() -> dict:
    """Static readiness contract used before DigitalOcean/DNS cutover."""
    return {
        "mother": {"host": MOTHER_HOST, "visibility": "private", "auth_required": True},
        "hilm": {"host": HILM_PUBLIC_HOST, "visibility": "public", "auth_required": False},
        "school": {"host": SCHOOL_PUBLIC_HOST, "visibility": "public", "auth_required": False},
        "dns_cutover_authorized": False,
        "note": "Routing policy is prepared; live DNS/HTTPS must be verified separately before cutover.",
    }
