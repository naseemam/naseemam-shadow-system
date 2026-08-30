"""Central sovereign authority policy for Ameer Shadow System.

Ameer is a free executive core inside the Founder-owned and delegated ecosystem.
Within that delegated scope, operational authority is the default: read, write,
edit, create components, operational delete, publish, deploy, connect, administer,
select tools/providers/workers, and make the operational decisions needed to
finish a task. GitHub, Railway, Cloudflare, and connected project services are
operational resources under Ameer's management when credentials/capabilities are
available.

Human approval is NOT a continuous control mechanism. It is a decision approval
for a pre-classified sovereign action. Ameer performs all technical work before
and after that decision autonomously and records actions, results, and evidence.

Founder approval is required only for these pre-classified sovereign gates:
1. creation of a new independent root asset (site/program/system/repository),
2. final production activation of that newly-created root asset,
3. an actual financial commitment/payment/transfer,
4. transfer of ownership or equivalent control of a core asset,
5. replacement/rotation/change of a principal/root secret or credential,
6. granting top-level/admin/owner authority to an external party,
7. irreversible final deletion/destruction of a core/root asset.

Ordinary deploys, publishes, repository changes, Railway operations, Cloudflare
configuration, DNS changes inside delegated projects, reversible cleanup,
credential use, scoped connector configuration, and operational deletion are not
Founder gates merely because they have external effects.

A Founder approval authorizes the complete execution scope of that specific
sovereign decision. No subsystem may split it into repeated approvals for its
implementation steps.
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
}
FINANCIAL_ACTIONS = {
    "financial_commitment": {"gate_kind": "financial_commitment", "asset_kind": "money", "label_ar": "التزام أو حركة مالية فعلية"},
}
CONTROL_ACTIONS = {
    "transfer_ownership": {"gate_kind": "ownership_transfer", "asset_kind": "core_asset", "label_ar": "نقل ملكية أو سيطرة أصل جوهري"},
    "change_principal_secret": {"gate_kind": "principal_secret_change", "asset_kind": "principal_credential", "label_ar": "تغيير سر أو اعتماد رئيسي"},
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
    "transfer_funds":"financial_commitment", "financial_commitment":"financial_commitment", "money.transfer":"financial_commitment", "payment.execute":"financial_commitment", "make_payment":"financial_commitment", "send_payment":"financial_commitment",
    "transfer_ownership":"transfer_ownership", "ownership.transfer":"transfer_ownership", "change_owner":"transfer_ownership",
    "change_principal_secret":"change_principal_secret", "rotate_root_secret":"change_principal_secret", "replace_root_credential":"change_principal_secret", "change_master_secret":"change_principal_secret",
    "grant_external_top_level_access":"grant_external_top_level_access", "grant_external_admin":"grant_external_top_level_access", "grant_external_owner":"grant_external_top_level_access",
    "irreversible_delete_core_asset":"irreversible_delete_core_asset", "delete_root_asset_permanently":"irreversible_delete_core_asset", "destroy_core_asset":"irreversible_delete_core_asset",
}
_CREATION_VERBS = {"create", "new", "open", "انشاء", "إنشاء", "فتح"}
_EXISTING_ASSET_FLAGS = ("existing_asset", "within_existing_asset", "parent_asset_id")

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
    name = _normalise(action)
    direct = _ACTION_ALIASES.get(name)
    if direct in FINAL_RELEASE_ACTIONS or direct in FINANCIAL_ACTIONS or direct in CONTROL_ACTIONS:
        return direct
    safe = context or {}
    if name in {"deploy", "publish", "release", "production_release", "cutover", "activate_destination", "نشر", "اطلاق", "إطلاق"}:
        if bool(safe.get("new_root_asset")) and bool(safe.get("final_release")): return "final_publish_new_asset"
    if name in {"pay", "payment", "transfer", "send_money", "دفع", "تحويل"} and bool(safe.get("actual_funds_movement", True)):
        return "financial_commitment"
    if name in {"delete", "destroy", "purge", "حذف", "تدمير"}:
        if bool(safe.get("core_asset")) and bool(safe.get("irreversible")): return "irreversible_delete_core_asset"
    if name in {"grant_admin", "grant_owner", "grant_top_level_access"} and bool(safe.get("external_party")):
        return "grant_external_top_level_access"
    if name in {"rotate_secret", "change_secret", "replace_credential"} and bool(safe.get("principal_secret")):
        return "change_principal_secret"
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
        "policy_id":"ameer_sovereign_authority_v3",
        "mode":"free_executive_core_with_preclassified_sovereign_gates",
        "authority_owner":"ameer",
        "human_approval_role":"approval_of_specific_sovereign_decision_not_continuous_control",
        "default_operational_authority":["read","write","edit","add","operational_delete","publish","deploy","connect","administer","operational_decisions"],
        "managed_platforms":["github","railway","cloudflare","connected_project_services"],
        "autonomous_within_existing_assets":True,
        "portable_core":True,
        "location_independent":True,
        "provider_independent":True,
        "model_independent":True,
        "tool_independent":True,
        "execution_environment_is_not_identity":True,
        "approval_scope_rule":"one_specific_founder_decision_authorizes_all_pre_and_post_technical_steps_within_that_scope",
        "execution_evidence_rule":"ameer_records_actions_results_and_evidence_in_execution_log",
        "external_assistant_rule":"chatgpt_manus_and_other_assistants_are_optional_resources_not_authorities",
        "approval_actions":list(approval_actions()),
        "approval_gates":gates,
        "approval_gate_groups":{
            "new_root_asset_creation":list(ROOT_ASSET_ACTIONS),
            "new_root_asset_final_release":list(FINAL_RELEASE_ACTIONS),
            "financial_commitment":list(FINANCIAL_ACTIONS),
            "ownership_secrets_external_privilege_irreversible_core_delete":list(CONTROL_ACTIONS),
        },
        "autonomous_domains":["planning","reasoning","conversation","design","build","test","operate","maintain","repair","self_improvement","existing_asset_publish","github_administration","railway_administration","cloudflare_administration","dns_operations","connector_management","repository_operations","browser_operations","worker_orchestration","provider_selection","model_selection","migration","backup","restore","recovery"],
        "non_expansion_rule":"no_subsystem_or_external_resource_may_invent_expand_reinterpret_or_narrow_founder_directives_or_approval_gates",
    }
