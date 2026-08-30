from kernel.ameer_authority import canonical_sovereign_action, policy_snapshot


def test_scoped_operational_key_creation_is_autonomous():
    assert canonical_sovereign_action("create_key", {"principal_secret": False}) is None


def test_expired_operational_token_rotation_is_autonomous():
    assert canonical_sovereign_action("rotate_token", {"principal_secret": False, "expired": True}) is None


def test_principal_root_credential_change_is_sovereign():
    assert canonical_sovereign_action("create_key", {"principal_secret": True}) == "change_principal_secret"


def test_revocation_that_can_interrupt_service_requires_founder_decision():
    assert canonical_sovereign_action(
        "revoke_token",
        {"may_interrupt_service": True, "replacement_verified": False},
    ) == "revoke_service_critical_credential"


def test_safe_retirement_after_verified_replacement_is_autonomous():
    assert canonical_sovereign_action(
        "revoke_token",
        {"may_interrupt_service": True, "replacement_verified": True},
    ) is None


def test_migration_preparation_and_deployment_are_autonomous():
    for action in ["deploy", "publish", "create_key", "rotate_token"]:
        assert canonical_sovereign_action(action, {"existing_asset": True, "principal_secret": False}) is None


def test_final_public_domain_cutover_is_sovereign():
    assert canonical_sovereign_action(
        "domain_cutover",
        {"final_public_cutover": True},
    ) == "final_domain_cutover"


def test_non_final_dns_preparation_is_autonomous():
    assert canonical_sovereign_action(
        "domain_cutover",
        {"final_public_cutover": False},
    ) is None


def test_policy_requires_pre_cutover_evidence():
    snap = policy_snapshot()
    assert "presents_pre_cutover_verification" in snap["execution_evidence_rule"]
    assert "final_public_domain_cutover_requires_founder_approval" in snap["migration_rule"]
