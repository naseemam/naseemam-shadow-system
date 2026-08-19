"""Central authority policy for Ameer Shadow System.

The Founder delegates operating authority to Ameer inside every already-approved
shadow asset.  A Founder decision is required only before Ameer creates a new
root digital asset: a site, program, system, or repository.

This module intentionally answers *authority*, not *capability*.  Callers must
still enforce a valid Guardian result, an available capability, the worker
scope, and evidence recording before they execute an operation.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, Mapping, Optional


ROOT_ASSET_ACTIONS: Dict[str, Dict[str, str]] = {
    "create_site": {
        "asset_kind": "site",
        "label_ar": "إنشاء موقع جديد",
        "description_ar": "إنشاء موقع مستقل جديد خارج الأصول القائمة.",
    },
    "create_program": {
        "asset_kind": "program",
        "label_ar": "إنشاء برنامج جديد",
        "description_ar": "إنشاء برنامج مستقل جديد خارج الأصول القائمة.",
    },
    "create_system": {
        "asset_kind": "system",
        "label_ar": "إنشاء نظام جديد",
        "description_ar": "إنشاء نظام مستقل جديد خارج الأصول القائمة.",
    },
    "create_repository": {
        "asset_kind": "repository",
        "label_ar": "إنشاء مستودع جديد",
        "description_ar": "إنشاء مستودع مستقل جديد خارج المستودعات القائمة.",
    },
}

_ASSET_KIND_ALIASES = {
    "site": "site",
    "website": "site",
    "web_site": "site",
    "موقع": "site",
    "برنامج": "program",
    "program": "program",
    "application": "program",
    "app": "program",
    "تطبيق": "program",
    "system": "system",
    "نظام": "system",
    "repository": "repository",
    "repo": "repository",
    "git_repository": "repository",
    "مستودع": "repository",
}

_ACTION_ALIASES = {
    "create_site": "create_site",
    "site.create": "create_site",
    "website.create": "create_site",
    "create_website": "create_site",
    "new_site": "create_site",
    "new_website": "create_site",
    "انشاء_موقع": "create_site",
    "إنشاء_موقع": "create_site",
    "فتح_موقع_جديد": "create_site",
    "create_program": "create_program",
    "program.create": "create_program",
    "application.create": "create_program",
    "app.create": "create_program",
    "new_program": "create_program",
    "new_application": "create_program",
    "انشاء_برنامج": "create_program",
    "إنشاء_برنامج": "create_program",
    "فتح_برنامج_جديد": "create_program",
    "create_system": "create_system",
    "system.create": "create_system",
    "new_system": "create_system",
    "انشاء_نظام": "create_system",
    "إنشاء_نظام": "create_system",
    "فتح_نظام_جديد": "create_system",
    "create_repository": "create_repository",
    "repository.create": "create_repository",
    "github.create_repository": "create_repository",
    "repo.create": "create_repository",
    "new_repository": "create_repository",
    "انشاء_مستودع": "create_repository",
    "إنشاء_مستودع": "create_repository",
    "فتح_مستودع_جديد": "create_repository",
}

_CREATION_VERBS = {"create", "new", "open", "انشاء", "إنشاء", "فتح"}
_EXISTING_ASSET_FLAGS = ("existing_asset", "within_existing_asset", "parent_asset_id")


def _normalise(value: object) -> str:
    """Return a stable action token without changing the caller's payload."""
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")


def _context_value(context: Optional[Mapping[str, Any]], *names: str) -> object:
    if not isinstance(context, Mapping):
        return None
    for name in names:
        value = context.get(name)
        if value not in (None, ""):
            return value
    return None


def _targets_existing_asset(context: Optional[Mapping[str, Any]]) -> bool:
    if not isinstance(context, Mapping):
        return False
    if any(bool(context.get(flag)) for flag in _EXISTING_ASSET_FLAGS):
        return True
    scope = _normalise(context.get("creation_scope"))
    return scope in {"component", "existing", "existing_asset", "child", "module"}


def _asset_kind(context: Optional[Mapping[str, Any]]) -> str:
    raw = _normalise(_context_value(context, "asset_kind", "root_asset_kind", "resource_kind", "target_kind"))
    return _ASSET_KIND_ALIASES.get(raw, "")


def canonical_creation_action(action: str, context: Optional[Mapping[str, Any]] = None) -> Optional[str]:
    """Return the canonical root-creation action, or ``None``.

    An explicit root-creation action always maps to one of the four gates unless
    the caller explicitly states that the work is a component within an existing
    asset.  Generic ``create`` is a gate only if its context identifies a root
    asset kind.  This keeps page, module, worker, and feature creation autonomous.
    """
    if _targets_existing_asset(context):
        return None

    name = _normalise(action)
    direct = _ACTION_ALIASES.get(name)
    if direct:
        return direct

    kind = _asset_kind(context)
    if kind and name in {_normalise(verb) for verb in _CREATION_VERBS}:
        return f"create_{kind}"
    return None


def is_root_asset_creation(action: str, context: Optional[Mapping[str, Any]] = None) -> bool:
    """Return whether the request opens a new root digital asset."""
    return canonical_creation_action(action, context) is not None


def requires_founder_approval(action: str, context: Optional[Mapping[str, Any]] = None) -> bool:
    """The single approval rule: only creation of a new root asset is gated."""
    return is_root_asset_creation(action, context)


def approval_actions() -> Iterable[str]:
    """Return canonical approval actions in a stable display order."""
    return tuple(ROOT_ASSET_ACTIONS.keys())


def policy_snapshot() -> Dict[str, Any]:
    """Return a safe, user-visible summary of Ameer's operating authority."""
    gates = [
        {"action": action, **details}
        for action, details in ROOT_ASSET_ACTIONS.items()
    ]
    return {
        "policy_id": "ameer_shadow_authority_v1",
        "mode": "autonomous_with_root_asset_creation_gate",
        "authority_owner": "ameer",
        "founder_approval_rule": "new_root_asset_creation_only",
        "autonomous_within_existing_assets": True,
        "approval_actions": list(approval_actions()),
        "approval_gates": gates,
        "autonomous_domains": [
            "planning",
            "design",
            "build",
            "test",
            "operate",
            "publish",
            "communications",
            "worker_orchestration",
            "school",
            "store",
            "trading",
        ],
        "worker_rule": "workers_execute_through_ameer_with_scoped_capabilities",
    }
