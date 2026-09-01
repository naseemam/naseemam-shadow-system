from kernel.guardian_policy_v2 import guardian_check_v2, validate_request_shape


def test_ordinary_execution_is_not_high_risk_gate():
    for action in (
        "execute", "deploy", "publish", "push", "edit_code", "run_tests", "send_email",
        "browse", "click", "fill_form", "delete_component", "rollback_existing_service",
    ):
        result = guardian_check_v2(action)
        assert result["status"] == "pass"
        assert result["approval_action"] is None
        assert result["authority_source"] == "ameer_authority"


def test_new_root_asset_creation_is_sovereign_gate():
    result = guardian_check_v2("create_site")
    assert result["status"] == "needs_approval"
    assert result["approval_action"] == "create_site"


def test_final_release_of_new_root_asset_is_sovereign_gate():
    result = guardian_check_v2("publish", context={"new_root_asset": True, "final_release": True})
    assert result["status"] == "needs_approval"
    assert result["approval_action"] == "final_publish_new_asset"


def test_actual_money_movement_is_sovereign_gate():
    result = guardian_check_v2("transfer_funds", context={"actual_funds_movement": True})
    assert result["status"] == "needs_approval"
    assert result["approval_action"] == "transfer_funds"


def test_payment_preparation_is_not_money_gate():
    result = guardian_check_v2("prepare_payment", context={"actual_funds_movement": False})
    assert result["status"] == "pass"


def test_technical_validation_failure_does_not_invent_founder_approval():
    result = validate_request_shape(action="")
    assert result["valid"] is False
    assert result["approval_required"] is False
