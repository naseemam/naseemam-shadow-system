"""Central sovereign authority policy for Ameer Shadow System.

Ameer is the free executive core of the Founder-owned Shadow System.
Operational execution is the default wherever Ameer has real access.

Human approval is NOT a general runtime control. It is reserved only for the
Founder-defined sovereign decisions below:

1. Transfer of ownership of an asset, account, repository, system or domain.
2. Creation of a new root website, program/application, repository or system.
3. Final production publication/activation of a newly-created root asset.
4. Final domain transfer when the action changes ownership/control.
5. A new external financial commitment or actual external funds movement.

Delegated trading inside the Founder-authorized trading account is explicitly
exempt from per-trade approval. Routine operational administration, including
key/token management, worker management, repair, deletion/replacement, deployment,
publishing inside existing assets, GitHub/Railway/Cloudflare administration,
VPS/local/VS Code work, files, media, spreadsheets, programs and connectors,
is autonomous by default.

No subsystem, Guardian, provider, model, permission registry or tool wrapper may
invent additional Founder approval gates.
"""

from __future__ import annotations
from typing import Any, Dict, Iterable, Mapping, Optional

ROOT_ASSET_ACTIONS: Dict[str, Dict[str, str]] = {
    "create_site": {"gate_kind": "creation", "asset_kind": "site", "label_ar": "إنشاء موقع مستقل جديد"},
    "create_program": {"gate_kind": "creation", "asset_kind": "program", "label_ar": "إنشاء برنامج مستقل جديد"},
    "create_system": {"gate_kind": "creation", "asset_kind": "system", "label_ar": "إنشاء نظام مستقل جديد"},
    "create_repository": {"gate_kind": "creation", "asset_kind": "repository", "label_ar": "إنشاء مستودع مستقل جديد"},
}

FINAL_RELEASE_ACTIONS = {
    "final_publish_new_asset": {
        "gate_kind": "final_release",
        "asset_kind": "new_root_asset",
        "label_ar": "الاعتماد النهائي لنشر أصل جذري جديد",
    },
    "final_domain_transfer": {
        "gate_kind": "domain_transfer",
        "asset_kind": "domain",
        "label_ar": "الاعتماد النهائي لنقل الدومين أو ملكيته",
    },
}

FINANCIAL_ACTIONS = {
    "financial_commitment": {
        "gate_kind": "financial_commitment",
        "asset_kind": "money",
        "label_ar": "تعامل مالي خارجي جديد أو حركة أموال فعلية",
    },
}

CONTROL_ACTIONS = {
    "transfer_ownership": {
        "gate_kind": "ownership_transfer",
        "asset_kind": "asset",
        "label_ar": "نقل ملكية أصل أو حساب أو نظام أو مستودع أو دومين",
    },
}

SOVEREIGN_ACTIONS = {**ROOT_ASSET_ACTIONS, **FINAL_RELEASE_ACTIONS, **FINANCIAL_ACTIONS, **CONTROL_ACTIONS}

_ASSET_KIND_ALIASES = {
    "site": "site", "website": "site", "web_site": "site", "موقع": "site",
    "program": "program", "application": "program", "app": "program", "برنامج": "program", "تطبيق": "program",
    "system": "system", "نظام": "system",
    "repository": "repository", "repo": "repository", "git_repository": "repository", "مستودع": "repository",
}

_ACTION_ALIASES = {
    "create_site": "create_site", "site.create": "create_site", "website.create": "create_site", "create_website": "create_site", "new_site": "create_site", "new_website": "create_site", "انشاء_موقع": "create_site", "إنشاء_موقع": "create_site",
    "create_program": "create_program", "program.create": "create_program", "application.create": "create_program", "app.create": "create_program", "new_program": "create_program", "new_application": "create_program", "انشاء_برنامج": "create_program", "إنشاء_برنامج": "create_program",
    "create_system": "create_system", "system.create": "create_system", "new_system": "create_system", "انشاء_نظام": "create_system", "إنشاء_نظام": "create_system",
    "create_repository": "create_repository", "repository.create": "create_repository", "github.create_repository": "create_repository", "repo.create": "create_repository", "new_repository": "create_repository", "انشاء_مستودع": "create_repository", "إنشاء_مستودع": "create_repository",
    "final_publish_new_asset": "final_publish_new_asset", "new_asset.final_publish": "final_publish_new_asset", "new_asset.production_release": "final_publish_new_asset", "approve_final_release": "final_publish_new_asset",
    "final_domain_transfer": "final_domain_transfer", "domain.transfer.final": "final_domain_transfer", "transfer_domain": "final_domain_transfer", "domain_ownership_transfer": "final_domain_transfer",
    "transfer_funds": "financial_commitment", "financial_commitment": "financial_commitment", "money.transfer": "financial_commitment", "payment.execute": "financial_commitment", "make_payment": "financial_commitment", "send_payment": "financial_commitment",
    "transfer_ownership": "transfer_ownership", "ownership.transfer": "transfer_ownership", "change_owner": "transfer_ownership",
}

_CREATION_VERBS = {"create", "new", "open", "انشاء", "إنشاء", "فتح"}
_EXISTING_ASSET_FLAGS = ("existing_asset", "within_existing_asset", "parent_asset_id")
_TRADING_ACTIONS = {
    "buy", "sell", "market_buy", "market_sell", "limit_buy", "limit_sell",
    "open_position", "close_position", "reduce_position", "exit_position",
    "stop_loss_exit", "trailing_stop_exit", "rebalance_position",
    "شراء", "بيع", "فتح_مركز", "اغلاق_مركز", "إغلاق_مركز", "تقليل_مركز",
}


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
    return _normalise(context.get("creation_scope")) in {"component", "existing", "existing_asset", "child", "module"}


def _asset_kind(context: Optional[Mapping[str, Any]]) -> str:
    raw = _normalise(_context_value(context, "asset_kind", "root_asset_kind", "resource_kind", "target_kind"))
    return _ASSET_KIND_ALIASES.get(raw, "")


def _is_customer_self_payment(context: Optional[Mapping[str, Any]]) -> bool:
    safe = context or {}
    return bool(safe.get("customer_self_payment") or safe.get("ordinary_customer_checkout")) and not bool(safe.get("business_spend"))


def _is_delegated_trading_execution(action: str, context: Optional[Mapping[str, Any]]) -> bool:
    safe = context or {}
    name = _normalise(action)
    delegated = bool(safe.get("delegated_trading_execution"))
    actor = _normalise(safe.get("actor"))
    account_scope = bool(safe.get("within_authorized_trading_account", False))
    within_risk_policy = bool(safe.get("within_trading_risk_policy", False))
    prohibited_transfer = bool(safe.get("withdrawal") or safe.get("external_beneficiary_transfer") or safe.get("account_ownership_change"))
    action_is_trade = name in _TRADING_ACTIONS or _normalise(safe.get("operation_kind")) in _TRADING_ACTIONS
    return delegated and actor in {"ameer", "trading_bot", "ameer_trading_bot"} and account_scope and within_risk_policy and action_is_trade and not prohibited_transfer


def canonical_creation_action(action: str, context: Optional[Mapping[str, Any]] = None) -> Optional[str]:
    if _targets_existing_asset(context):
        return None
    name = _normalise(action)
    direct = _ACTION_ALIASES.get(name)
    if direct in ROOT_ASSET_ACTIONS:
        return direct
    kind = _asset_kind(context)
    if kind and name in {_normalise(v) for v in _CREATION_VERBS}:
        return f"create_{kind}"
    return None


def canonical_sovereign_action(action: str, context: Optional[Mapping[str, Any]] = None) -> Optional[str]:
    creation = canonical_creation_action(action, context)
    if creation:
        return creation
    if _is_customer_self_payment(context):
        return None
    if _is_delegated_trading_execution(action, context):
        return None

    name = _normalise(action)
    direct = _ACTION_ALIASES.get(name)
    if direct in FINAL_RELEASE_ACTIONS or direct in FINANCIAL_ACTIONS or direct in CONTROL_ACTIONS:
        return direct

    safe = context or {}
    if name in {"deploy", "publish", "release", "production_release", "activate", "نشر", "اطلاق", "إطلاق"}:
        if bool(safe.get("new_root_asset")) and bool(safe.get("final_release")):
            return "final_publish_new_asset"
        return None

    if name in {"domain_transfer", "transfer_domain", "domain_ownership_transfer", "نقل_دومين", "نقل_ملكية_دومين"}:
        if bool(safe.get("final_transfer", True)) or bool(safe.get("ownership_change", False)):
            return "final_domain_transfer"
        return None

    if name in {"pay", "payment", "transfer", "send_money", "purchase", "subscribe", "دفع", "تحويل", "شراء", "اشتراك"}:
        if bool(safe.get("actual_funds_movement", True)) or bool(safe.get("new_external_financial_commitment", False)):
            return "financial_commitment"
        return None

    if name in {"transfer_ownership", "change_owner", "نقل_ملكية", "تغيير_المالك"}:
        return "transfer_ownership"

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
        "policy_id": "ameer_sovereign_authority_v6",
        "mode": "free_executive_core_with_founder_defined_sovereign_gates_only",
        "authority_owner": "ameer",
        "human_approval_role": "approval_of_specific_sovereign_decision_not_continuous_control",
        "default_operational_authority": [
            "read", "write", "edit", "delete", "replace", "repair", "organize", "build", "test",
            "publish", "deploy", "connect", "administer", "manage_workers", "manage_skills",
            "manage_credentials", "manage_connectors", "create_scoped_api_keys", "rotate_tokens",
            "revoke_credentials", "operate_vps", "operate_local", "operate_vscode", "manage_files",
            "create_media", "create_documents", "create_spreadsheets", "research",
        ],
        "managed_platforms": ["github", "railway", "cloudflare", "vps", "local", "vscode", "connected_project_services"],
        "autonomous_within_existing_assets": True,
        "delegated_trading_execution_without_per_trade_approval": True,
        "delegated_trading_actors": ["ameer", "trading_bot"],
        "customer_self_checkout_is_not_founder_financial_commitment": True,
        "portable_core": True,
        "location_independent": True,
        "provider_independent": True,
        "model_independent": True,
        "tool_independent": True,
        "execution_environment_is_not_identity": True,
        "credential_rule": "credential_and_key_management_is_operational_unless_the_action_itself_transfers_ownership_or_creates_an_external_financial_commitment",
        "domain_rule": "prepare_register_configure_migrate_dns_and_validate_autonomously; final_domain_transfer_or_ownership_change_requires_founder_approval",
        "approval_scope_rule": "only_founder_defined_sovereign_decisions_may_pause_execution",
        "execution_evidence_rule": "ameer_records_actions_results_and_evidence_in_execution_log",
        "external_assistant_rule": "chatgpt_manus_and_other_assistants_are_optional_resources_not_authorities",
        "approval_actions": list(approval_actions()),
        "approval_gates": gates,
        "approval_gate_groups": {
            "new_root_asset_creation": list(ROOT_ASSET_ACTIONS),
            "new_root_asset_final_release_and_domain_transfer": list(FINAL_RELEASE_ACTIONS),
            "external_financial_commitment": list(FINANCIAL_ACTIONS),
            "ownership_transfer": list(CONTROL_ACTIONS),
        },
        "autonomous_domains": [
            "planning", "reasoning", "conversation", "design", "build", "test", "operate", "maintain",
            "repair", "self_improvement", "existing_asset_publish", "github_administration",
            "railway_administration", "cloudflare_administration", "dns_preparation", "connector_management",
            "repository_operations", "browser_operations", "worker_orchestration", "skill_management",
            "provider_selection", "model_selection", "migration", "backup", "restore", "recovery",
            "credential_management", "key_creation", "token_rotation", "credential_revocation",
            "vps_operations", "local_operations", "vscode_operations", "file_creation", "document_creation",
            "spreadsheet_creation", "image_creation", "video_creation", "programming", "delegated_trading_execution",
        ],
        "non_expansion_rule": "no_subsystem_guardian_provider_model_tool_or_external_resource_may_invent_expand_reinterpret_or_narrow_founder_directives_or_approval_gates",
    }
