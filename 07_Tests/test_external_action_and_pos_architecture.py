from kernel.external_action_orchestration import ordinary_device_operation_contract, travel_booking_contract
from kernel.pos_invoicing_architecture import architecture_snapshot


def test_routine_authorized_device_operation_does_not_invent_founder_approval():
    contract = ordinary_device_operation_contract()
    assert contract["routine_operation_requires_founder_approval"] is False
    assert contract["policy_layer_may_not_invent_human_approval"] is True


def test_travel_booking_is_prepared_end_to_end_before_final_commitment():
    contract = travel_booking_contract()
    assert contract["research_and_preparation_are_autonomous"] is True
    assert "hotel_research" in contract["supported_scope"]
    assert "reservation_preparation" in contract["supported_scope"]
    assert contract["final_financial_commitment_uses_sovereign_gate"] is True
    assert contract["execution_continues_after_founder_decision"] is True


def test_pos_is_offline_first_and_web_connected():
    snap = architecture_snapshot()
    assert snap["single_source_of_truth"] is True
    assert snap["pos_supports_web_and_local_operation"] is True
    assert snap["invoicing_supports_web_and_local_operation"] is True
    assert snap["local_sales_must_continue_during_internet_outage"] is True
    assert snap["local_invoicing_must_continue_during_internet_outage"] is True
    assert snap["sync_after_connectivity_returns"] is True
    assert "point_of_sale" in snap["modules"]
    assert "invoicing" in snap["modules"]
    assert "background_sync_queue" in snap["local_runtime"]
    assert "central_api" in snap["web_runtime"]
    assert "web_pos" in snap["web_runtime"]
    assert "web_invoicing" in snap["web_runtime"]
    assert snap["ameer_may_design_build_test_operate_and_evolve_system"] is True


def test_pos_operator_and_management_surfaces_are_separate():
    snap = architecture_snapshot()
    assert snap["operator_and_management_surfaces_are_separate"] is True
    assert "reception_employee_login" in snap["pos_operator_surface"]
    assert "consume_existing_booking_without_duplicate_entry" in snap["pos_operator_surface"]
    assert "no_service_price_administration" in snap["pos_operator_surface"]
    assert "founder_access" in snap["pos_management_surface"]
    assert "ameer_operational_access" in snap["pos_management_surface"]
    assert "manage_pos_roles_and_delegations" in snap["pos_management_surface"]


def test_invoicing_operator_and_management_surfaces_are_separate():
    snap = architecture_snapshot()
    assert "authorized_employee_login" in snap["invoicing_operator_surface"]
    assert "create_invoice_from_booking_pos_or_order" in snap["invoicing_operator_surface"]
    assert "no_invoice_policy_administration" in snap["invoicing_operator_surface"]
    assert "founder_access" in snap["invoicing_management_surface"]
    assert "ameer_operational_access" in snap["invoicing_management_surface"]
    assert "manage_invoicing_roles_and_delegations" in snap["invoicing_management_surface"]


def test_management_delegation_is_scoped_and_does_not_transfer_ownership():
    snap = architecture_snapshot()
    rules = set(snap["delegation_rules"])
    assert snap["named_employee_management_delegation_supported"] is True
    assert snap["operator_role_never_implies_management_role"] is True
    assert "delegation_may_be_full_or_capability_scoped" in rules
    assert "delegation_must_be_audited" in rules
    assert "delegation_may_be_revoked_or_modified" in rules
    assert "delegation_does_not_transfer_ownership" in rules
    assert "delegation_does_not_reduce_ameer_operational_oversight" in rules
