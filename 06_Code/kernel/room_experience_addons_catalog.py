"""Catalog-driven room experience add-ons for Hilm Alnada.

Celebration-room and VIP/relaxation-room bookings do not maintain a separate price
list. They project selectable services from the canonical Hilm catalog so the
customer can combine room time with coffee, food, spa/massage, facial, Moroccan
bath when priced/enabled, bridal makeup and other eligible services. Checkout uses
the canonical current price and availability for every selected item.
"""

from dataclasses import dataclass
from typing import Dict, Tuple


# Verified from the current Hilm Alnada catalog images. Values are SAR.
VERIFIED_CATALOG_PRICES: Dict[str, int] = {
    # Celebration packages
    "celebration_basic_package": 450,
    "celebration_distinguished_package": 650,
    "celebration_luxury_package": 850,
    # Relaxation room
    "relaxation_room_30_minutes": 80,
    "relaxation_room_60_minutes": 120,
    "relaxation_room_vip_90_minutes": 180,
    # Bridal / makeup
    "bridal_makeup": 800,
    # Facial examples
    "deep_skin_cleaning": 250,
    "vip_skin_cleaning": 350,
    "hydrafacial": 499,
    "acne_facial": 350,
    "collagen_facial": 399,
    # Massage examples
    "classic_relaxation_massage_60": 400,
    "classic_swedish_massage_60": 500,
    "classic_hot_stone_massage_60": 550,
    "specialized_hot_stone_massage_90": 800,
    # Coffee / food examples
    "espresso": 18,
    "americano": 22,
    "cappuccino": 24,
    "latte": 24,
    "spanish_latte": 26,
    "flat_white": 28,
    "hot_chocolate": 20,
    "iced_americano": 20,
    "iced_latte": 24,
    "sparkling_iced_latte": 26,
    "caramel_iced_latte": 26,
    "peach_iced_tea": 22,
    "lemon_iced_tea": 22,
    "mango_passion_fruit_mojito": 24,
    "strawberry_mojito": 24,
    "mixed_berries_mojito": 24,
    "date_cake": 24,
    "tiramisu": 20,
    "brownie_chocolate": 18,
    "mini_pancake": 20,
    "margherita_pizza": 28,
    "vegetable_pizza": 32,
    "chicken_pizza": 34,
    "ranch_chicken_pizza": 36,
    "mini_chicken_sandwich": 18,
    "mini_cheese_sandwich": 18,
}

ROOM_BOOKING_SURFACES: Tuple[str, ...] = (
    "celebration_room",
    "vip_room",
    "relaxation_room",
)

ADDON_CATEGORIES: Tuple[str, ...] = (
    "celebration_package",
    "coffee_hot_beverages",
    "coffee_cold_beverages",
    "desserts_and_cakes",
    "food_and_snacks",
    "massage_and_spa",
    "facial",
    "moroccan_bath",
    "bridal_services",
    "makeup",
    "custom_request",
)

ROOM_EXPERIENCE_BOOKING_FLOW: Tuple[str, ...] = (
    "select_room_surface",
    "select_room_package_or_duration",
    "load_eligible_addons_from_canonical_catalog",
    "show_each_addon_with_current_catalog_price",
    "select_zero_or_more_addons",
    "capture_quantity_and_service_time_when_applicable",
    "check_room_service_staff_and_resource_availability",
    "recalculate_total_from_canonical_prices",
    "show_itemized_booking_summary",
    "checkout_through_shared_payment_gateway",
    "verify_payment_server_side",
    "create_single_composite_booking",
    "reserve_room_and_link_service_bookings",
    "send_preparation_tasks_to_relevant_departments",
    "hilm_follows_customer_and_coordinates_selected_services",
)

CATALOG_LINK_RULES: Tuple[str, ...] = (
    "room_addons_reference_canonical_catalog_item_ids",
    "room_addons_never_duplicate_or_fork_service_prices",
    "price_is_reloaded_at_checkout",
    "inactive_or_unavailable_catalog_items_cannot_be_selected",
    "moroccan_bath_appears_only_when_a_canonical_price_is_configured",
    "selected_addon_preserves_price_snapshot_on_confirmed_booking",
    "coffee_food_and_service_quantities_are_itemized",
    "all_selected_items_share_one_customer_booking_summary_and_payment",
)


@dataclass(frozen=True)
class RoomExperienceAddonsContract:
    celebration_room_uses_catalog_packages: bool = True
    vip_and_relaxation_rooms_support_catalog_addons: bool = True
    coffee_items_selectable_with_prices: bool = True
    spa_and_massage_items_selectable_with_prices: bool = True
    facial_items_selectable_with_prices: bool = True
    bridal_services_selectable_with_prices: bool = True
    moroccan_bath_selectable_when_canonical_price_exists: bool = True
    addons_use_current_canonical_catalog_prices: bool = True
    room_and_addons_use_shared_checkout: bool = True
    single_composite_booking_coordinates_all_departments: bool = True
    hilm_coordinates_selected_experience_end_to_end: bool = True


def room_experience_addons_contract() -> RoomExperienceAddonsContract:
    return RoomExperienceAddonsContract()
