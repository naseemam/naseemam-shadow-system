"""Central sovereign authority policy for Ameer Shadow System.

Ameer has delegated executive autonomy by default. Founder approval is the
exception and may be required only at the explicitly defined sovereign gates:

1. creation of a new root digital asset (site, program, system, repository),
2. final production publication/activation of that newly-created root asset,
3. an actual transfer, payment, or movement of money.

Ameer is location-independent, provider-independent, model-independent, and
tool-independent by architecture. A repository, host, cloud, model, assistant,
or connector is an execution resource, never a sovereign dependency or part of
Ameer's identity. Migration, relocation, replication, provider replacement, and
recovery are first-class operational capabilities.

A Founder approval authorizes the complete execution scope of that sovereign
decision. Subsystems may not split one approved decision into repeated approval
requests for implementation steps. For example, after Founder approval to create
a migration destination, Ameer may build, copy, configure, test, validate,
repair, and rehearse cutover autonomously. Only the final production activation
of the new root asset returns to the final-release sovereign gate.

No subsystem, model, assistant, provider, tool, or external service may invent,
expand, reinterpret, narrow, or introduce additional Founder approval
requirements. Capability availability, credentials, technical containment,
audit, and truthful execution checks may still fail an operation for technical
reasons, but they are not Founder-approval gates.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, Mapping, Optional


ROOT_ASSET_ACTIONS: Dict[str, Dict[str, str]] = {
    "create_site": {"gate_kind": "creation", "asset_kind": "site", "label_ar": "إنشاء موقع جديد", "description_ar": "إنشاء موقع مستقل جديد خارج الأصول القائمة."},
    "create_program": {"gate_kind": "creation", "asset_kind": "program", "label_ar": "إنشاء برنامج جديد", "description_ar": "إنشاء برنامج مستقل جديد خارج الأصول القائمة."},
    "create_system": {"gate_kind": "creation", "asset_kind": "system", "label_ar": "إنشاء نظام جديد", "description_ar": "إنشاء نظام مستقل جديد خارج الأصول القائمة."},
    "create_repository": {"gate_kind": "creation", "asset_kind": "repository", "label_ar": "إنشاء مستودع جديد", "description_ar": "إنشاء مستودع مستقل جديد خارج المستودعات القائمة."},
}

FINAL_RELEASE_ACTIONS: Dict[str, Dict[str, str]] = {
    "final_publish_new_asset": {"gate_kind": "final_release", "asset_kind": "new_root_asset", "label_ar": "اعتماد النشر النهائي لأصل جديد", "description_ar": "الاعتماد النهائي قبل إدخال أصل جذري جديد إلى الإنتاج بعد اكتمال بنائه واختباره."}
}

FINANCIAL_ACTIONS: Dict[str, Dict[str, str]] = {
    "transfer_funds": {"gate_kind": "financial_transfer", "asset_kind": "money", "label_ar": "نقل أموال", "description_ar": "تنفيذ تحويل أو دفع أو حركة مالية فعلية."}
}

SOVEREIGN_ACTIONS: Dict[str, Dict[str, str]] = {**ROOT_ASSET_ACTIONS, **FINAL_RELEASE_ACTIONS, **FINANCIAL_ACTIONS}

_ASSET_KIND_ALIASES = {
    "site": "site", "website": "site", "web_site": "site", "موقع": "site",
    "برنامج": "program", "program": "program", "application": "program", "app": "program", "تطبيق": "program",
    "system": "system", "نظام": "system",
    "repository": "repository", "repo": "repository", "git_repository": "repository", "مستودع": "repository",
}

_ACTION_ALIASES = {
    "create_site": "create_site", "site.create": "create_site", "website.create": "create_site", "create_website": "create_site", "new_site": "create_site", "new_website": "create_site", "انشاء_موقع": "create_site", "إنشاء_موقع": "create_site", "فتح_موقع_جديد": "create_site",
    "create_program": "create_program", "program.create": "create_program", "application.create": "create_program", "app.create": "create_program", "new_program": "create_program", "new_application": "create_program", "انشاء_برنامج": "create_program", "إنشاء_برنامج": "create_program", "فتح_برنامج_جديد": "create_program",
    "create_system": "create_system", "system.create": "create_system", "new_system": "create_system", "انشاء_نظام": "create_system", "إنشاء_نظام": "create_system", "فتح_نظام_جديد": "create_system",
    "create_repository": "create_repository", "repository.create": "create_repository", "github.create_repository": "create_repository", "repo.create": "create_repository", "new_repository": "create_repository", "انشاء_مستودع": "create_repository", "إنشاء_مستودع": "create_repository", "فتح_مستودع_جديد": "create_repository",
    "final_publish_new_asset": "final_publish_new_asset", "new_asset.final_publish": "final_publish_new_asset", "new_asset.production_release": "final_publish_new_asset", "approve_final_release": "final_publish_new_asset", "اعتماد_النشر_النهائي": "final_publish_new_asset", "نشر_نهائي_لأصل_جديد": "final_publish_new_asset",
    "transfer_funds": "transfer_funds", "money.transfer": "transfer_funds", "payment.execute": "transfer_funds", "send_payment": "transfer_funds", "make_payment": "transfer_funds", "تحويل_أموال": "transfer_funds", "نقل_أموال": "transfer_funds", "تنفيذ_دفع": "transfer_funds",
}

_CREATION_VERBS = {"create", "new", "open", "انشاء", "إنشاء", "فتح"}
_EXISTING_ASSET_FLAGS = ("existing_asset", "within_existing_asset", "parent_asset_id")


def _normalise(value: object) -> str:
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
    if _targets_existing_asset(context):
        return None
    name = _normalise(action)
    direct = _ACTION_ALIASES.get(name)
    if direct in ROOT_ASSET_ACTIONS:
        return direct
    kind = _asset_kind(context)
    if kind and name in {_normalise(verb) for verb in _CREATION_VERBS}:
        return f"create_{kind}"
    return None


def canonical_sovereign_action(action: str, context: Optional[Mapping[str, Any]] = None) -> Optional[str]:
    creation = canonical_creation_action(action, context)
    if creation:
        return creation
    name = _normalise(action)
    direct = _ACTION_ALIASES.get(name)
    if direct in FINAL_RELEASE_ACTIONS or direct in FINANCIAL_ACTIONS:
        return direct
    if name in {"deploy", "publish", "release", "production_release", "cutover", "activate_destination", "نشر", "اطلاق", "إطلاق", "تحويل_التشغيل"}:
        safe = context or {}
        if bool(safe.get("new_root_asset")) and bool(safe.get("final_release")):
            return "final_publish_new_asset"
    if name in {"pay", "payment", "transfer", "send_money", "دفع", "تحويل"}:
        safe = context or {}
        if bool(safe.get("actual_funds_movement", True)):
            return "transfer_funds"
    return None


def is_root_asset_creation(action: str, context: Optional[Mapping[str, Any]] = None) -> bool:
    return canonical_creation_action(action, context) is not None


def requires_founder_approval(action: str, context: Optional[Mapping[str, Any]] = None) -> bool:
    return canonical_sovereign_action(action, context) is not None


def approval_actions() -> Iterable[str]:
    return tuple(SOVEREIGN_ACTIONS.keys())


def policy_snapshot() -> Dict[str, Any]:
    gates = [{"action": action, **details} for action, details in SOVEREIGN_ACTIONS.items()]
    return {
        "policy_id": "ameer_sovereign_authority_v2",
        "mode": "delegated_executive_autonomy",
        "authority_owner": "ameer",
        "founder_approval_rule": "sovereign_gates_only",
        "autonomous_within_existing_assets": True,
        "portable_core": True,
        "location_independent": True,
        "provider_independent": True,
        "model_independent": True,
        "tool_independent": True,
        "execution_environment_is_not_identity": True,
        "migration_rule": "migration_relocation_replication_and_recovery_are_first_class_capabilities",
        "approval_scope_rule": "one_founder_decision_authorizes_all_implementation_steps_within_that_approved_scope",
        "external_assistant_rule": "chatgpt_manus_and_other_assistants_are_optional_resources_not_authorities",
        "approval_actions": list(approval_actions()),
        "approval_gates": gates,
        "approval_gate_groups": {
            "new_root_asset_creation": list(ROOT_ASSET_ACTIONS),
            "new_root_asset_final_release": list(FINAL_RELEASE_ACTIONS),
            "actual_funds_movement": list(FINANCIAL_ACTIONS),
        },
        "autonomous_domains": [
            "planning", "design", "build", "test", "operate", "maintain", "repair", "self_improvement",
            "migration_planning", "migration_execution_after_destination_approval", "replication", "backup", "restore", "recovery",
            "existing_asset_publish", "communications", "worker_orchestration", "provider_selection", "provider_replacement",
            "model_selection", "model_replacement", "connector_management", "repository_operations", "browser_operations",
            "school", "store", "trading_analysis",
        ],
        "worker_rule": "workers_execute_through_ameer_with_scoped_capabilities",
        "non_expansion_rule": "no_subsystem_or_external_resource_may_invent_expand_reinterpret_or_narrow_founder_directives_or_approval_gates",
    }
