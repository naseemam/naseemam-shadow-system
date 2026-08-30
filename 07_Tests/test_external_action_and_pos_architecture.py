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
    assert snap["local_sales_must_continue_during_internet_outage"] is True
    assert snap["sync_after_connectivity_returns"] is True
    assert "point_of_sale" in snap["modules"]
    assert "invoicing" in snap["modules"]
    assert "background_sync_queue" in snap["local_runtime"]
    assert "central_api" in snap["web_runtime"]
    assert snap["ameer_may_design_build_test_operate_and_evolve_system"] is True
