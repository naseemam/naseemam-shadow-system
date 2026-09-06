from kernel.ameer_authority import canonical_sovereign_action, policy_snapshot, requires_founder_approval


def test_existing_asset_operations_are_autonomous():
    for action in [
        "read", "write", "edit", "delete", "replace", "repair", "deploy", "publish",
        "push", "dns_update", "railway_deploy", "create_key", "rotate_token", "revoke_token",
        "manage_worker", "update_skill", "create_file", "create_image", "create_video",
    ]:
        assert requires_founder_approval(action, {"existing_asset": True}) is False


def test_platform_administration_is_default_operational_authority():
    snap = policy_snapshot()
    assert set(["github", "railway", "cloudflare", "vps", "local", "vscode"]).issubset(set(snap["managed_platforms"]))
    assert "deploy" in snap["default_operational_authority"]
    assert "manage_workers" in snap["default_operational_authority"]
    assert "manage_skills" in snap["default_operational_authority"]
    assert "manage_credentials" in snap["default_operational_authority"]
    assert snap["human_approval_role"] == "approval_of_specific_sovereign_decision_not_continuous_control"


def test_removed_legacy_control_gates_are_operational():
    assert canonical_sovereign_action("delete", {"core_asset": True, "irreversible": True}) is None
    assert canonical_sovereign_action("grant_admin", {"external_party": True}) is None
    assert canonical_sovereign_action("create_key", {"principal_secret": True}) is None
    assert canonical_sovereign_action("rotate_secret", {"principal_secret": True}) is None
    assert canonical_sovereign_action("revoke_token", {"may_interrupt_service": True}) is None


def test_financial_commitment_is_specific_gate():
    assert canonical_sovereign_action("payment", {"actual_funds_movement": True}) == "financial_commitment"
    assert canonical_sovereign_action("payment", {"actual_funds_movement": False}) is None


def test_ownership_transfer_is_specific_gate():
    assert canonical_sovereign_action("transfer_ownership", {"core_asset": True}) == "transfer_ownership"


def test_new_root_asset_creation_requires_founder_decision():
    assert canonical_sovereign_action("create_site") == "create_site"
    assert canonical_sovereign_action("create_program") == "create_program"
    assert canonical_sovereign_action("create_repository") == "create_repository"
    assert canonical_sovereign_action("create_system") == "create_system"


def test_existing_asset_component_creation_is_autonomous():
    assert canonical_sovereign_action("create_site", {"existing_asset": True}) is None
    assert canonical_sovereign_action("create_program", {"creation_scope": "module"}) is None


def test_final_release_of_new_root_asset_is_sovereign_existing_publish_is_not():
    assert canonical_sovereign_action("publish", {"new_root_asset": True, "final_release": True}) == "final_publish_new_asset"
    assert canonical_sovereign_action("publish", {"existing_asset": True}) is None


def test_execution_log_evidence_is_part_of_policy_contract():
    snap = policy_snapshot()
    assert snap["execution_evidence_rule"] == "ameer_records_actions_results_and_evidence_in_execution_log"
    assert snap["non_expansion_rule"].startswith("no_subsystem_guardian_provider_model_tool")
