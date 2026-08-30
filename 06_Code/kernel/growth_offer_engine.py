"""Autonomous commercial growth loop for Hilm Alnada.

Ameer should not wait for the Founder to manually invent every offer or campaign.
It detects opportunities from business data and the calendar, designs operational
offers, creates the campaign assets, distributes them through authenticated channels,
updates offer surfaces in the website/store, and measures the result. A separate
sovereign gate applies only when an action crosses a preclassified sovereign boundary,
such as an actual paid advertising commitment.
"""

from dataclasses import dataclass
from typing import Tuple


SIGNALS: Tuple[str, ...] = (
    "low_booking_day",
    "low_occupancy_window",
    "underused_service_provider",
    "service_demand_change",
    "inventory_opportunity",
    "seasonal_event",
    "eid_campaign_window",
    "national_or_local_occasion",
    "customer_segment_opportunity",
    "conversion_dropoff",
)

CAMPAIGN_SURFACES: Tuple[str, ...] = (
    "website_offers_section",
    "store_offers_section",
    "storefront_banner",
    "service_catalog_promotion",
    "tiktok_account",
    "social_media_creative",
    "customer_message_channel",
)

CREATIVE_ASSETS: Tuple[str, ...] = (
    "offer_image",
    "campaign_banner",
    "tiktok_short_video",
    "promotional_video",
    "service_visual",
    "offer_copy",
    "caption",
    "call_to_action",
)

ACTIONS: Tuple[str, ...] = (
    "monitor_business_calendar",
    "detect_seasonal_or_idle_opportunity",
    "analyze_signal",
    "select_target_segment",
    "select_services_and_providers",
    "calculate_offer_margin",
    "design_offer",
    "generate_copy",
    "generate_offer_images",
    "generate_tiktok_video",
    "generate_campaign_video",
    "prepare_campaign",
    "update_website_offers_section",
    "update_store_offers_section",
    "publish_when_authenticated_connector_available",
    "measure_conversion",
    "compare_against_baseline",
    "iterate_or_retire_offer",
)


@dataclass(frozen=True)
class GrowthOfferEngineContract:
    waits_for_founder_to_create_offer: bool = False
    waits_for_founder_to_request_campaign: bool = False
    may_create_operational_offer: bool = True
    may_generate_ad_creatives: bool = True
    may_generate_offer_images: bool = True
    may_generate_tiktok_video: bool = True
    may_update_website_and_store_offers: bool = True
    may_publish_via_authenticated_connector: bool = True
    must_monitor_seasonal_events_and_idle_days: bool = True
    must_measure_results: bool = True
    paid_media_financial_commitment_uses_existing_sovereign_gate: bool = True


def growth_offer_engine_contract() -> GrowthOfferEngineContract:
    return GrowthOfferEngineContract()
