from kernel.ameer_authority import canonical_sovereign_action, policy_snapshot


def test_all_credential_management_is_operational_by_default():
    cases = [
        ("create_key", {"principal_secret": False}),
        ("create_key", {"principal_secret": True}),
        ("rotate_token", {"principal_secret": False, "expired": True}),
        ("rotate_secret", {"principal_secret": True}),
        ("revoke_token", {"may_interrupt_service": True, "replacement_verified": False}),
        ("revoke_token", {"may_interrupt_service": True, "replacement_verified": True}),
    ]
    for action, context in cases:
        assert canonical_sovereign_action(action, context) is None


def test_migration_preparation_and_existing_asset_deployment_are_autonomous():
    for action in ["deploy", "publish", "create_key", "rotate_token", "dns_update", "configure_domain"]:
        assert canonical_sovereign_action(action, {"existing_asset": True}) is None


def test_final_domain_transfer_is_sovereign():
    assert canonical_sovereign_action(
        "transfer_domain",
        {"final_transfer": True},
    ) == "final_domain_transfer"


def test_domain_preparation_without_final_transfer_is_autonomous():
    assert canonical_sovereign_action(
        "transfer_domain",
        {"final_transfer": False},
    ) is None
    assert canonical_sovereign_action("dns_update", {"existing_asset": True}) is None


def test_policy_states_domain_and_credential_rules():
    snap = policy_snapshot()
    assert "final_domain_transfer_or_ownership_change_requires_founder_approval" in snap["domain_rule"]
    assert snap["credential_rule"].startswith("credential_and_key_management_is_operational")
