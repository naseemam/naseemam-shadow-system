"""Central sovereign authority policy for Ameer Shadow System.

Ameer is a free executive core inside the Founder-owned and delegated ecosystem.
Operational authority is the default inside delegated projects. Founder approval
is reserved for pre-classified sovereign decisions, not routine execution.

Two financial cases are explicitly outside the Founder financial gate:
* an ordinary customer paying for the customer's own purchase/booking; and
* delegated investment trading executed by Ameer or the trading bot inside the
  Founder-authorized trading account and configured risk policy.

The trading exception authorizes market execution (buy/sell/open/close/reduce and
risk exits) without per-trade approval. It does not authorize unrelated business
spend, withdrawals, transfers to external beneficiaries, changing account
ownership, or expanding the delegated capital/account scope.
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
    "final_publish_new_asset": {"gate_kind": "final_release", "asset_kind": "new_root_asset", "label_ar": "اعتماد التفعيل الإنتاجي النهائي لأصل جديد"},
    "final_domain_cutover": {"gate_kind": "final_domain_cutover", "asset_kind": "public_domain", "label_ar": "اعتماد تحويل الدومين النهائي"},
}
FINANCIAL_ACTIONS = {
    "financial_commitment": {"gate_kind": "financial_commitment", "asset_kind": "money", "label_ar": "التزام أو حركة مالية فعلية"},
}
CONTROL_ACTIONS = {
    "transfer_ownership": {"gate_kind": "ownership_transfer", "asset_kind": "core_asset", "label_ar": "نقل ملكية أو سيطرة أصل جوهري"},
    "change_principal_secret": {"gate_kind": "principal_secret_change", "asset_kind": "principal_credential", "label_ar": "إنشاء أو استبدال سر أو اعتماد رئيسي"},
    "revoke_service_critical_credential": {"gate_kind": "service_critical_credential_revocation", "asset_kind": "credential", "label_ar": "إلغاء اعتماد حي قد يقطع الخدمة"},
    "grant_external_top_level_access": {"gate_kind": "external_privilege_grant", "asset_kind": "authority", "label_ar": "منح طرف خارجي صلاحيات عليا"},
    "irreversible_delete_core_asset": {"gate_kind": "irreversible_core_deletion", "asset_kind": "core_asset", "label_ar": "الحذف النهائي غير القابل للتراجع لأصل جوهري"},
}
SOVEREIGN_ACTIONS = {**ROOT_ASSET_ACTIONS, **FINAL_RELEASE_ACTIONS, **FINANCIAL_ACTIONS, **CONTROL_ACTIONS}

_ASSET_KIND_ALIASES = {
    "site":"site", "website":"site", "web_site":"site", "موقع":"site",
    "program":"program", "application":"program", "app":"program", "برنامج":"program", "تطبيق":"program",
    "system":"system", "نظام":"system",
    "repository":"repository", "repo":"repository", "git_repository":"repository", "مستودع":"repository",
}
_ACTION_ALIASES = {
    "create_site":"create_site", "site.create":"create_site", "website.create":"create_site", "create_website":"create_site", "new_site":"create_site", "new_website":"create_site", "انشاء_موقع":"create_site", "إنشاء_موقع":"create_site",
    "create_program":"create_program", "program.create":"create_program", "application.create":"create_program", "app.create":"create_program", "new_program":"create_program", "new_application":"create_program", "انشاء_برنامج":"create_program", "إنشاء_برنامج":"create_program",
    "create_system":"create_system", "system.create":"create_system", "new_system":"create_system", "انشاء_نظام":"create_system", "إنشاء_نظام":"create_system",
    "create_repository":"create_repository", "repository.create":"create_repository", "github.create_repository":"create_repository", "repo.create":"create_repository", "new_repository":"create_repository", "انشاء_مستودع":"create_repository", "إنشاء_مستودع":"create_repository",
    "final_publish_new_asset":"final_publish_new_asset", "new_asset.final_publish":"final_publish_new_asset", "new_asset.production_release":"final_publish_new_asset", "approve_final_release":"final_publish_new_asset",
    "final_domain_cutover":"final_domain_cutover", "domain.final_cutover":"final_domain_cutover", "dns.final_cutover":"final_domain_cutover", "switch_public_domain":"final_domain_cutover",
    "transfer_funds":"financial_commitment", "financial_commitment":"financial_commitment", "money.transfer":"financial_commitment", "payment.execute":"financial_commitment", "make_payment":"financial_commitment", "send_payment":"financial_commitment",
    "transfer_ownership":"transfer_ownership", "ownership.transfer":"transfer_ownership", "change_owner":"transfer_ownership",
    "change_principal_secret":"change_principal_secret", "create_root_secret":"change_principal_secret", "replace_root_credential":"change_principal_secret", "change_master_secret":"change_principal_secret",
    "revoke_service_critical_credential":"revoke_service_critical_credential", "revoke_live_credential":"revoke_service_critical_credential",
    "grant_external_top_level_access":"grant_external_top_level_access", "grant_external_admin":"grant_external_top_level_access", "grant_external_owner":"grant_external_top_level_access",
    "irreversible_delete_core_asset":"irreversible_delete_core_asset", "delete_root_asset_permanently":"irreversible_delete_core_asset", "destroy_core_asset":"irreversible_delete_core_asset",
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
    if not isinstance(context, Mapping): return None
    for name in names:
        value = context.get(name)
        if value not in (None, ""): return value
    return None

def _targets_existing_asset(context: Optional[Mapping[str, Any]]) -> bool:
    if not isinstance(context, Mapping): return False
    if any(bool(context.get(flag)) for flag in _EXISTING_ASSET_FLAGS): return True
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
    if _targets_existing_asset(context): return None
    name = _normalise(action)
    direct = _ACTION_ALIASES.get(name)
    if direct in ROOT_ASSET_ACTIONS: return direct
    kind = _asset_kind(context)
    if kind and name in {_normalise(v) for v in _CREATION_VERBS}: return f"create_{kind}"
    return None

def canonical_sovereign_action(action: str, context: Optional[Mapping[str, Any]] = None) -> Optional[str]:
    creation = canonical_creation_action(action, context)
    if creation: return creation
    if _is_customer_self_payment(context): return None
    if _is_delegated_trading_execution(action, context): return None
    name = _normalise(action)
    direct = _ACTION_ALIASES.get(name)
    if direct in FINAL_RELEASE_ACTIONS or direct in FINANCIAL_ACTIONS or direct in CONTROL_ACTIONS:
        return direct
    safe = context or {}
    if name in {"deploy", "publish", "release", "production_release", "cutover", "activate_destination", "نشر", "اطلاق", "إطلاق"}:
        if bool(safe.get("new_root_asset")) and bool(safe.get("final_release")): return "final_publish_new_asset"
    if name in {"dns_cutover", "domain_cutover", "switch_domain", "switch_dns", "تحويل_الدومين", "تحويل_dns"} and bool(safe.get("final_public_cutover")):
        return "final_domain_cutover"
    if name in {"pay", "payment", "transfer", "send_money", "دفع", "تحويل"} and bool(safe.get("actual_funds_movement", True)):
        return "financial_commitment"
    if name in {"delete", "destroy", "purge", "حذف", "تدمير"} and bool(safe.get("core_asset")) and bool(safe.get("irreversible")):
        return "irreversible_delete_core_asset"
    if name in {"grant_admin", "grant_owner", "grant_top_level_access"} and bool(safe.get("external_party")):
        return "grant_external_top_level_access"
    if name in {"create_key", "create_token", "rotate_key", "rotate_token", "replace_credential", "change_secret"}:
        if bool(safe.get("principal_secret")) or bool(safe.get("root_credential")): return "change_principal_secret"
        return None
    if name in {"revoke_key", "revoke_token", "disable_credential", "delete_key", "delete_token"}:
        if bool(safe.get("may_interrupt_service")) and not bool(safe.get("replacement_verified")):
            return "revoke_service_critical_credential"
        return None
    if name in {"transfer_ownership", "change_owner"} and bool(safe.get("core_asset", True)):
        return "transfer_ownership"
    return None

def is_root_asset_creation(action: str, context: Optional[Mapping[str, Any]] = None) -> bool:
    return canonical_creation_action(action, context) is not None

def requires_founder_approval(action: str, context: Optional[Mapping[str, Any]] = None) -> bool:
    return canonical_sovereign_action(action, context) is not None

def approval_actions() -> Iterable[str]: return tuple(SOVEREIGN_ACTIONS.keys())

def policy_snapshot() -> Dict[str, Any]:
    gates = [{"action": action, **details} for action, details in SOVEREIGN_ACTIONS.items()]
    return {
        "policy_id":"ameer_sovereign_authority_v5",
        "mode":"free_executive_core_with_preclassified_sovereign_gates",
        "authority_owner":"ameer",
        "human_approval_role":"approval_of_specific_sovereign_decision_not_continuous_control",
        "default_operational_authority":["read","write","edit","add","operational_delete","publish","deploy","connect","administer","operational_decisions","create_scoped_api_keys","rotate_operational_tokens"],
        "managed_platforms":["github","railway","cloudflare","connected_project_services"],
        "autonomous_within_existing_assets":True,
        "delegated_trading_execution_without_per_trade_approval":True,
        "delegated_trading_actors":["ameer","trading_bot"],
        "trading_exception_scope":"buy_sell_open_close_reduce_and_risk_exit_inside_authorized_account_and_risk_policy_only",
        "customer_self_checkout_is_not_founder_financial_commitment":True,
        "portable_core":True,
        "location_independent":True,
        "provider_independent":True,
        "model_independent":True,
        "tool_independent":True,
        "execution_environment_is_not_identity":True,
        "credential_rotation_rule":"scoped_or_expired_operational_key_rotation_is_autonomous; principal_credential_change_or_unverified_service_critical_revocation_is_sovereign",
        "migration_rule":"prepare_configure_deploy_test_repair_and_validate_destination_autonomously; final_public_domain_cutover_requires_founder_approval",
        "approval_scope_rule":"one_specific_founder_decision_authorizes_all_pre_and_post_technical_steps_within_that_scope",
        "execution_evidence_rule":"ameer_records_actions_results_and_evidence_in_execution_log_and_presents_pre_cutover_verification",
        "external_assistant_rule":"chatgpt_manus_and_other_assistants_are_optional_resources_not_authorities",
        "approval_actions":list(approval_actions()),
        "approval_gates":gates,
        "approval_gate_groups":{
            "new_root_asset_creation":list(ROOT_ASSET_ACTIONS),
            "new_root_asset_final_release_and_domain_cutover":list(FINAL_RELEASE_ACTIONS),
            "financial_commitment":list(FINANCIAL_ACTIONS),
            "ownership_credentials_external_privilege_irreversible_core_delete":list(CONTROL_ACTIONS),
        },
        "autonomous_domains":["planning","reasoning","conversation","design","build","test","operate","maintain","repair","self_improvement","existing_asset_publish","github_administration","railway_administration","cloudflare_administration","dns_preparation","connector_management","repository_operations","browser_operations","worker_orchestration","provider_selection","model_selection","migration","backup","restore","recovery","scoped_key_creation","operational_key_rotation","expired_key_replacement","delegated_trading_execution"],
        "non_expansion_rule":"no_subsystem_or_external_resource_may_invent_expand_reinterpret_or_narrow_founder_directives_or_approval_gates",
    }
