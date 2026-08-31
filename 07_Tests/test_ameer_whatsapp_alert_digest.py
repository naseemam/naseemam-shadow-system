from 06_Code.kernel.ameer_whatsapp_alert_digest import alert_digest_contract


def test_purchase_alerts_are_consolidated_before_whatsapp():
    contract = alert_digest_contract()
    rules = contract["rules"]
    assert rules["do_not_send_one_whatsapp_message_per_item"] is True
    assert rules["aggregate_purchase_items_into_one_clear_report"] is True
    assert rules["deduplicate_repeated_alerts"] is True
    assert contract["purchase_alert_style"] == "single_analyzed_digest_not_item_spam"


def test_purchase_digest_contains_counts_balances_and_priority():
    fields = set(alert_digest_contract()["purchase_digest_fields"])
    required = {
        "total_distinct_items",
        "total_requested_units",
        "requested_quantity",
        "current_balance",
        "minimum_level",
        "reason",
        "priority",
        "department_breakdown",
        "supplier_grouping",
    }
    assert required.issubset(fields)


def test_whatsapp_is_delivery_channel_only_after_ameer_review():
    contract = alert_digest_contract()
    assert contract["review_chain"] == [
        "specialized_worker",
        "ameer",
        "founder_whatsapp_when_needed",
    ]
    rules = contract["rules"]
    assert rules["whatsapp_is_delivery_channel_not_source_of_truth"] is True
    assert rules["send_only_when_whatsapp_connector_is_authenticated_and_healthy"] is True
    assert rules["never_claim_delivery_without_connector_result"] is True
