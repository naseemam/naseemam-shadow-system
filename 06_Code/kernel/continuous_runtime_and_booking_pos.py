"""Always-on runtime semantics and booking-to-POS handoff for Hilm Alnada."""

from __future__ import annotations

from typing import Dict, Tuple


AMEER_RUNTIME_POLICY: Dict[str, object] = {
    "availability": "continuous_24_24",
    "requires_founder_presence": False,
    "requires_chat_open": False,
    "requires_manual_start_each_day": False,
    "work_hours_model": None,
    "pause_rule": "only_for_explicit_shutdown_or_unrecoverable_technical_dependency",
    "resume_rule": "restore_state_and_continue_persistent_goals_automatically",
}


BOOKING_POS_FLOW: Tuple[str, ...] = (
    "store_booking_created",
    "booking_number_assigned",
    "booking_synced_to_single_source_of_truth",
    "booking_visible_in_reception_pos",
    "reception_opens_booking_by_number_or_customer",
    "verify_customer_service_time_price",
    "issue_invoice_from_booking",
    "collect_payment_if_due",
    "print_customer_receipt",
    "print_or_display_service_handoff_slip",
    "handoff_to_assigned_service_employee",
    "update_booking_and_sale_status",
)


def reception_booking_view() -> Dict[str, object]:
    return {
        "visible_fields": [
            "booking_number",
            "customer_name",
            "customer_contact_masked_as_needed",
            "service",
            "scheduled_time",
            "assigned_employee_if_set",
            "price",
            "payment_status",
            "booking_status",
        ],
        "allowed_actions": [
            "search_booking",
            "open_booking",
            "issue_invoice",
            "collect_payment",
            "print_receipt",
            "print_service_handoff",
            "mark_arrived",
            "handoff_to_service_employee",
        ],
        "forbidden_admin_domains": [
            "payroll",
            "employee_hr_records",
            "full_inventory_admin",
            "supplier_management",
            "financial_analytics",
            "system_settings",
        ],
    }


def booking_pos_policy_snapshot() -> Dict[str, object]:
    return {
        "runtime": AMEER_RUNTIME_POLICY,
        "booking_pos_flow": list(BOOKING_POS_FLOW),
        "reception_view": reception_booking_view(),
        "source_of_truth": "shared_central_business_data_layer",
        "no_duplicate_entry": True,
    }
