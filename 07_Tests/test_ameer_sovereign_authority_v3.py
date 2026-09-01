from kernel.ameer_authority import canonical_sovereign_action, policy_snapshot, requires_founder_approval


def test_existing_asset_operations_are_autonomous():
    for action in ["read", "write", "edit", "delete", "deploy", "publish", "push", "dns_update", "railway_deploy"]:
        assert requires_founder_approval(action, {"existing_asset": True}) is False


def test_platform_administration_is_default_operational_authority():
    snap = policy_snapshot()
    assert set(["github", "railway", "cloudflare"]).issubset(set(snap["managed_platforms"]))
    assert "deploy" in snap["default_operational_authority"]
    assert snap["human_approval_role"] == "approval_of_specific_sovereign_decision_not_continuous_control"


def test_irreversible_core_delete_is_sovereign_but_operational_delete_is_not():
    assert canonical_sovereign_action("delete", {"existing_asset": True, "core_asset": False, "irreversible": False}) is None
    assert canonical_sovereign_action("delete", {"core_asset": True, "irreversible": True}) == "irreversible_delete_core_asset"


def test_external_top_level_grant_is_sovereign_but_internal_scoped_permissions_are_not():
    assert canonical_sovereign_action("grant_admin", {"external_party": True}) == "grant_external_top_level_access"
    assert canonical_sovereign_action("grant_admin", {"external_party": False}) is None


def test_principal_secret_change_is_sovereign_not_ordinary_secret_use():
    assert canonical_sovereign_action("rotate_secret", {"principal_secret": True}) == "change_principal_secret"
    assert canonical_sovereign_action("use_secret", {"principal_secret": True}) is None


def test_financial_commitment_is_specific_gate():
    assert canonical_sovereign_action("payment", {"actual_funds_movement": True}) == "financial_commitment"
    assert canonical_sovereign_action("payment", {"actual_funds_movement": False}) is None


def test_ownership_transfer_is_specific_gate():
    assert canonical_sovereign_action("transfer_ownership", {"core_asset": True}) == "transfer_ownership"


def test_execution_log_evidence_is_part_of_policy_contract():
    snap = policy_snapshot()
    assert snap["execution_evidence_rule"] == "ameer_records_actions_results_and_evidence_in_execution_log"
