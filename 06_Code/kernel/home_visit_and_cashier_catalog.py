"""Home-visit pricing and cashier catalog synchronization for Hilm Alnada.

The uploaded Hilm Alnada catalog remains the canonical base-price source. Eligible
home-visit services use a fixed 10% uplift that is folded into the customer-facing
final price. The cashier consumes the complete canonical service catalog and prices
rather than maintaining a separate manually-entered price list.
"""

from dataclasses import dataclass
from typing import Tuple

from .hilm_catalog_and_booking_rules import CATALOG_SECTIONS, SERVICE_CATALOG


HOME_VISIT_SECTION = "home_visit"
HOME_VISIT_UPLIFT_PERCENT = 10
HOME_VISIT_UPLIFT_RATE = HOME_VISIT_UPLIFT_PERCENT / 100


def catalog_service_rows() -> Tuple[dict, ...]:
    """Flatten every canonical catalog service for POS/cashier consumption."""
    rows = []
    for section in CATALOG_SECTIONS:
        for service in SERVICE_CATALOG.get(section, ()):
            rows.append({"section": section, **service})
    return tuple(rows)


CASHIER_SERVICE_CATALOG = catalog_service_rows()


def home_visit_price(service_name: str, base_price: float) -> dict:
    """Return the final customer-facing home-visit price with the 10% uplift included."""
    if base_price < 0:
        raise ValueError("base price cannot be negative")
    final_price = round(base_price * (1 + HOME_VISIT_UPLIFT_RATE), 2)
    return {
        "service_name": service_name,
        "final_price": final_price,
        "customer_price_label": final_price,
        "customer_sees_separate_home_visit_fee": False,
        "status": "priced",
    }


@dataclass(frozen=True)
class HomeVisitAndCashierContract:
    home_visit_is_store_section: bool = True
    home_visit_reuses_canonical_services: bool = True
    home_visit_uplift_percent: int = 10
    home_visit_final_price_includes_uplift: bool = True
    customer_sees_separate_home_visit_fee: bool = False
    cashier_uses_entire_canonical_catalog: bool = True
    cashier_uses_catalog_prices: bool = True
    cashier_must_not_have_duplicate_manual_price_source: bool = True
    storefront_cashier_management_share_service_ssot: bool = True


def home_visit_and_cashier_contract() -> HomeVisitAndCashierContract:
    return HomeVisitAndCashierContract()
