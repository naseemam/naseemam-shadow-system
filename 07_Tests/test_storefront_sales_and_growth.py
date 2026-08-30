from 06_Code.kernel.storefront_sales_agent import (
    CUSTOMER_JOURNEY,
    STOREFRONT_COMPONENTS,
    storefront_sales_agent_contract,
)
from 06_Code.kernel.growth_offer_engine import (
    ACTIONS,
    SIGNALS,
    growth_offer_engine_contract,
)


def test_storefront_is_24_24_sales_agent():
    contract = storefront_sales_agent_contract()
    assert contract.availability == "24/24"
    assert contract.waits_for_founder_to_open_chat is False
    assert contract.may_recommend_services is True
    assert contract.may_recommend_service_provider is True
    assert contract.may_create_booking is True
    assert contract.may_prepare_cart_and_checkout is True


def test_storefront_contains_full_commerce_and_booking_journey():
    required = {
        "service_categories",
        "service_catalog",
        "prices",
        "recommendations",
        "availability",
        "booking",
        "cart",
        "buy_now",
        "checkout",
        "payment",
        "booking_number",
        "employee_rating",
    }
    assert required.issubset(set(STOREFRONT_COMPONENTS))
    assert "recommend_service_provider" in CUSTOMER_JOURNEY
    assert "request_employee_rating" in CUSTOMER_JOURNEY


def test_growth_engine_does_not_wait_for_manual_offer_request():
    contract = growth_offer_engine_contract()
    assert contract.waits_for_founder_to_create_offer is False
    assert contract.waits_for_founder_to_request_campaign is False
    assert contract.may_create_operational_offer is True
    assert contract.may_generate_ad_creatives is True
    assert contract.must_measure_results is True
    assert "low_occupancy_window" in SIGNALS
    assert "calculate_offer_margin" in ACTIONS
    assert "publish_when_authenticated_connector_available" in ACTIONS
