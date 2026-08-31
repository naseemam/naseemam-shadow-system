"""Ameer-reviewed WhatsApp alert digests for Hilm Alnada operations.

Raw operational alerts must not be forwarded one-by-one to the Founder. Workers
(e.g. Nada) collect and normalize alerts; Ameer groups, analyzes and prioritizes
them, then sends a concise actionable digest through WhatsApp when that
connector is authenticated.
"""

from __future__ import annotations

from typing import Dict, Tuple


ALERT_CATEGORIES: Tuple[str, ...] = (
    "purchase_and_restock",
    "inventory_shortage",
    "inventory_variance",
    "damage_and_waste",
    "loss_or_misuse",
    "maintenance_and_breakdown",
    "asset_and_custody",
    "supplier_and_purchase_order",
    "expiry",
    "attendance_and_staffing",
    "quality_and_sanitation",
    "customer_or_booking_escalation",
    "financial_or_invoice_exception",
)

PURCHASE_DIGEST_FIELDS: Tuple[str, ...] = (
    "report_period",
    "total_distinct_items",
    "total_requested_units",
    "critical_item_count",
    "department_breakdown",
    "supplier_grouping",
    "item_name",
    "requested_quantity",
    "unit",
    "current_balance",
    "minimum_level",
    "reorder_target",
    "reason",
    "priority",
    "estimated_stockout_date_when_known",
)

DIGEST_RULES: Dict[str, object] = {
    "raw_alerts_go_to_worker_first": True,
    "nada_collects_inventory_and_purchase_alerts": True,
    "ameer_reviews_before_founder_notification": True,
    "do_not_send_one_whatsapp_message_per_item": True,
    "aggregate_purchase_items_into_one_clear_report": True,
    "group_by_department_and_supplier_when_useful": True,
    "include_quantities_and_units": True,
    "include_current_balance_and_minimum_level": True,
    "include_reason_and_priority": True,
    "deduplicate_repeated_alerts": True,
    "collapse_same_root_cause_alerts": True,
    "separate_urgent_from_routine": True,
    "routine_alerts_may_be_batched": True,
    "critical_service_interrupting_alerts_may_be_sent_immediately": True,
    "every_digest_is_printable_and_exportable_inside_management_program": True,
    "whatsapp_is_delivery_channel_not_source_of_truth": True,
    "canonical_alert_and_report_record_remains_in_management_system": True,
    "send_only_when_whatsapp_connector_is_authenticated_and_healthy": True,
    "never_claim_delivery_without_connector_result": True,
}


def alert_digest_contract() -> Dict[str, object]:
    return {
        "alert_categories": list(ALERT_CATEGORIES),
        "purchase_digest_fields": list(PURCHASE_DIGEST_FIELDS),
        "rules": dict(DIGEST_RULES),
        "review_chain": ["specialized_worker", "ameer", "founder_whatsapp_when_needed"],
        "purchase_alert_style": "single_analyzed_digest_not_item_spam",
        "ameer_may_recommend_consolidated_purchase_order": True,
        "ameer_may_group_items_by_supplier": True,
        "ameer_may_rank_by_stockout_risk_and_operational_impact": True,
    }
