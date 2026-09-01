from kernel.autonomous_execution_loop import cloudflare_operational_key_plan, decide_credential_step


def test_ameer_may_create_scoped_cloudflare_operational_key():
    decision = decide_credential_step(
        "create_key",
        context={"provider": "cloudflare", "principal_secret": False, "root_credential": False},
    )
    assert decision.may_execute is True
    assert decision.founder_approval_required is False


def test_ameer_may_replace_expired_operational_token():
    decision = decide_credential_step(
        "rotate_token",
        context={"provider": "cloudflare", "principal_secret": False, "expired": True},
    )
    assert decision.may_execute is True


def test_service_breaking_key_revocation_stops_at_sovereign_gate():
    decision = decide_credential_step(
        "revoke_key",
        context={"provider": "cloudflare", "may_interrupt_service": True, "replacement_verified": False},
        phase="retire_old_credential_if_safe",
    )
    assert decision.may_execute is False
    assert decision.founder_approval_required is True


def test_old_key_can_be_retired_after_verified_replacement():
    decision = decide_credential_step(
        "revoke_key",
        context={"provider": "cloudflare", "may_interrupt_service": True, "replacement_verified": True},
        phase="retire_old_credential_if_safe",
    )
    assert decision.may_execute is True
    assert decision.founder_approval_required is False


def test_cloudflare_plan_keeps_secret_values_out_of_evidence():
    plan = cloudflare_operational_key_plan(purpose="operate R2 for Ameer")
    assert any(step["phase"] == "create_operational_credential" for step in plan)
    evidence = [step for step in plan if step["phase"] == "record_credential_evidence"][0]
    assert evidence["redact_secret_value"] is True
