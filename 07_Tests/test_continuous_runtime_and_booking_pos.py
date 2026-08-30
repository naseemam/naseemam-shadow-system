from kernel.continuous_runtime_and_booking_pos import AMEER_RUNTIME_POLICY, BOOKING_POS_FLOW, reception_booking_view


def test_ameer_runtime_is_24_24_without_founder_presence():
    assert AMEER_RUNTIME_POLICY["availability"] == "continuous_24_24"
    assert AMEER_RUNTIME_POLICY["requires_founder_presence"] is False
    assert AMEER_RUNTIME_POLICY["requires_chat_open"] is False
    assert AMEER_RUNTIME_POLICY["requires_manual_start_each_day"] is False
    assert AMEER_RUNTIME_POLICY["work_hours_model"] is None


def test_store_booking_flows_into_reception_pos_without_duplicate_entry():
    assert BOOKING_POS_FLOW[0] == "store_booking_created"
    assert "booking_visible_in_reception_pos" in BOOKING_POS_FLOW
    assert "issue_invoice_from_booking" in BOOKING_POS_FLOW
    assert "print_service_handoff_slip" in BOOKING_POS_FLOW
    assert BOOKING_POS_FLOW[-1] == "update_booking_and_sale_status"


def test_reception_can_invoice_booking_but_cannot_see_admin_domains():
    view = reception_booking_view()
    assert "booking_number" in view["visible_fields"]
    assert "issue_invoice" in view["allowed_actions"]
    assert "print_service_handoff" in view["allowed_actions"]
    assert "payroll" in view["forbidden_admin_domains"]
    assert "employee_hr_records" in view["forbidden_admin_domains"]
