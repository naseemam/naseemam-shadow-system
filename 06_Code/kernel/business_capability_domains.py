"""Business, commerce, school-artifact, media and customer-journey capabilities.

These are first-class operational domains for Ameer.  Ameer may orchestrate the
available workers/tools/connectors needed to complete them instead of handing the
Founder a list of manual steps.
"""

from __future__ import annotations

from typing import Dict, Tuple


ARTIFACT_CAPABILITIES: Tuple[str, ...] = (
    "spreadsheet_xlsx",
    "tables_and_dashboards",
    "word_docx",
    "pdf",
    "presentation_pptx",
    "csv",
    "reports",
    "school_records",
    "inventory_records",
    "employee_records",
    "resource_records",
)

MEDIA_CAPABILITIES: Tuple[str, ...] = (
    "high_quality_image_generation",
    "high_quality_video_generation",
    "video_editing",
    "social_media_creatives",
    "offer_creatives",
    "product_and_service_visuals",
)

COMMERCE_OPERATIONS: Tuple[str, ...] = (
    "website_content_management",
    "store_management",
    "service_catalog_management",
    "offer_management",
    "inventory_management",
    "booking_management",
    "customer_management",
    "order_management",
    "checkout_journey_management",
    "analytics_and_conversion_review",
)

SOCIAL_OPERATIONS: Tuple[str, ...] = (
    "tiktok_content_planning",
    "tiktok_media_generation",
    "tiktok_publishing_when_connector_available",
    "campaign_management",
    "offer_distribution",
    "content_calendar",
    "performance_review",
)

CUSTOMER_JOURNEY_STAGES: Tuple[str, ...] = (
    "discovery",
    "service_browsing",
    "service_comparison",
    "recommendation",
    "availability",
    "booking_or_cart",
    "checkout",
    "purchase_confirmation",
    "pre_visit_followup",
    "visit_or_fulfilment",
    "post_purchase_followup",
    "review_and_retention",
)


def customer_journey_worker_contract() -> Dict[str, object]:
    return {
        "worker_role": "customer_journey_specialist",
        "mission": "own_and_optimize_customer_journey_from_first_interest_to_purchase_and_retention",
        "stages": list(CUSTOMER_JOURNEY_STAGES),
        "may_recommend_services": True,
        "may_coordinate_bookings": True,
        "may_coordinate_store_checkout": True,
        "may_analyze_dropoff": True,
        "may_propose_and_execute_operational_improvements": True,
        "founder_approval": "only_when_a_separate_preclassified_sovereign_gate_is_crossed",
    }


def business_capability_snapshot() -> Dict[str, object]:
    return {
        "artifact_generation": list(ARTIFACT_CAPABILITIES),
        "media_generation": list(MEDIA_CAPABILITIES),
        "commerce_operations": list(COMMERCE_OPERATIONS),
        "social_operations": list(SOCIAL_OPERATIONS),
        "customer_journey": customer_journey_worker_contract(),
        "execution_rule": "create_validate_repair_deliver_or_publish_using_available_tools_and_connectors",
        "provider_rule": "providers_are_replaceable_resources_not_authorities",
    }
