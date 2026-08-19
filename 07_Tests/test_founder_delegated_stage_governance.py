from kernel.stage_governance import StageGovernancePolicy


def test_ameer_has_autonomy_for_existing_assets_and_external_work():
    policy = StageGovernancePolicy()

    for action, external_effect, irreversible in (
        ("git.merge_main", True, False),
        ("credential.activate", True, True),
        ("external.send_sensitive", True, False),
        ("trading.execute", True, True),
        ("github.push", True, False),
        ("delete.repository_file", False, True),
        ("publish.external", True, False),
        ("railway.deploy_production", True, False),
        ("railway.rollback", True, True),
    ):
        decision = policy.evaluate(action, external_effect=external_effect, irreversible=irreversible)
        assert decision.decision == "ALLOW", action
        assert decision.approval_required is False, action


def test_only_new_root_assets_require_founder_approval():
    policy = StageGovernancePolicy()

    for action in (
        "create_site",
        "create_program",
        "create_system",
        "create_repository",
        "website.create",
        "github.create_repository",
    ):
        decision = policy.evaluate(action, external_effect=True, irreversible=True)
        assert decision.decision == "REQUIRE_APPROVAL", action
        assert decision.approval_required is True, action
        assert decision.reason == "founder_root_asset_creation_gate"


def test_components_created_inside_existing_asset_remain_delegated():
    policy = StageGovernancePolicy()
    decision = policy.evaluate("create_site", context={"within_existing_asset": True})
    assert decision.decision == "ALLOW"
    assert decision.approval_required is False
