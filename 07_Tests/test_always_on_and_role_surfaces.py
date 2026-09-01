from kernel.always_on_operations import always_on_operations_contract
from kernel.hilm_role_surfaces import role_surface_contract


def test_ameer_operates_without_founder_presence_or_open_chat():
    contract = always_on_operations_contract()
    assert contract["service_mode"] == "continuous_24_7"
    assert contract["requires_founder_presence"] is False
    assert contract["requires_chat_session_open"] is False
    assert contract["may_continue_persistent_goals"] is True
    assert contract["may_resume_after_restart"] is True


def test_ordinary_operations_continue_without_waiting_for_founder():
    contract = always_on_operations_contract()
    assert contract["ordinary_operational_work"] == "continue_without_waiting_for_founder"
    assert "websites" in contract["domains"]
    assert "repositories" in contract["domains"]
    assert "systems" in contract["domains"]


def test_management_surface_contains_full_business_administration():
    surfaces = role_surface_contract()
    modules = set(surfaces["management"]["modules"])
    assert {"inventory", "employees", "payroll", "customers", "reports", "permissions"}.issubset(modules)


def test_reception_only_gets_pos_and_invoice_workflow():
    surfaces = role_surface_contract()
    modules = set(surfaces["reception_pos"]["modules"])
    assert {"service_sale", "invoice_issue", "payment_collection", "receipt_printing"}.issubset(modules)
    assert "payroll" not in modules
    assert "inventory" not in modules


def test_restricted_management_data_is_not_merely_hidden_in_ui():
    surfaces = role_surface_contract()
    assert surfaces["authorization_rule"] == "enforce_server_side_not_ui_hiding_only"
    assert "payroll" in surfaces["reception_pos"]["must_not_expose"]
