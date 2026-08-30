"""Home-visit pricing and cashier catalog synchronization for Hilm Alnada.

The uploaded Hilm Alnada catalog remains the canonical base-price source. Home visits
reuse eligible catalog services and add a configurable per-service surcharge. The
cashier consumes the complete canonical service catalog and prices rather than
maintaining a separate manually-entered price list.
"""

from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from .hilm_catalog_and_booking_rules import CATALOG_SECTIONS, SERVICE_CATALOG


HOME_VISIT_SECTION = "home_visit"

# Founder has specified that every home-visit service carries an additional charge,
# but has not yet specified the amount for each service. Do not invent prices.
# Keys should be canonical service names from SERVICE_CATALOG.
HOME_VISIT_SURCHARGES: Dict[str, Optional[float]] = {
    service["name"]: None
    for section, services in SERVICE_CATALOG.items()
    if section not in {"coffee_lounge", "relaxation_room", "celebration_room", "offers"}
    for service in services
}


def catalog_service_rows() -> Tuple[dict, ...]:
    """Flatten every canonical catalog service for POS/cashier consumption."""
    rows = []
    for section in CATALOG_SECTIONS:
        for service in SERVICE_CATALOG.get(section, ()):
            rows.append({"section": section, **service})
    return tuple(rows)


CASHIER_SERVICE_CATALOG = catalog_service_rows()


def home_visit_price(service_name: str, base_price: float, surcharge: Optional[float]) -> dict:
    """Calculate a home-visit price without silently inventing a surcharge."""
    if surcharge is None:
        return {
            "service_name": service_name,
            "base_price": base_price,
            "home_visit_surcharge": None,
            "final_price": None,
            "status": "surcharge_configuration_required",
        }
    if surcharge < 0:
        raise ValueError("home visit surcharge cannot be negative")
    return {
        "service_name": service_name,
        "base_price": base_price,
        "home_visit_surcharge": surcharge,
        "final_price": base_price + surcharge,
        "status": "priced",
    }


@dataclass(frozen=True)
class HomeVisitAndCashierContract:
    home_visit_is_store_section: bool = True
    home_visit_reuses_canonical_services: bool = True
    home_visit_has_per_service_surcharge: bool = True
    home_visit_final_price_is_base_plus_surcharge: bool = True
    founder_controls_surcharge_amounts: bool = True
    cashier_uses_entire_canonical_catalog: bool = True
    cashier_uses_catalog_prices: bool = True
    cashier_must_not_have_duplicate_manual_price_source: bool = True
    storefront_cashier_management_share_service_ssot: bool = True


def home_visit_and_cashier_contract() -> HomeVisitAndCashierContract:
    return HomeVisitAndCashierContract()
