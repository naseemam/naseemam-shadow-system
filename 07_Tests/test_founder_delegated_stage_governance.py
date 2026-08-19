from kernel.stage_governance import StageGovernancePolicy


def test_ameer_has_autonomy_for_merge_activation_and_external_work():
    policy = StageGovernancePolicy()

    for action, external_effect, irreversible in (
        ("git.merge_main", True, False),
        ("credential.activate", True, True),
        ("external.send_sensitive", True, False),
        ("trading.execute", True, True),
        ("github.push", True, False),
    ):
        decision = policy.evaluate(action, external_effect=external_effect, irreversible=irreversible)
        assert decision.decision == "ALLOW", action
        assert decision.approval_required is False, action


def test_only_delete_and_publish_require_founder_final_approval():
    policy = StageGovernancePolicy()

    for action in (
        "delete",
        "destructive.delete",
        "delete.repository_file",
        "publish",
        "publish.external",
        "railway.deploy_production",
        "railway.rollback",
    ):
        decision = policy.evaluate(action, external_effect=True, irreversible=True)
        assert decision.decision == "REQUIRE_APPROVAL", action
        assert decision.approval_required is True, action
        assert decision.reason == "founder_delete_or_publish_gate"
