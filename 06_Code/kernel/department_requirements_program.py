"""Department requirements, setup, maintenance and damage tracking for Hilm Alnada.

The canonical department list is derived from the Hilm Alnada service catalog.
Exact assets, brands and quantities are not invented when the catalog does not
specify them. Those values remain setup fields to be confirmed by management or
the department lead before purchase.

Home visits are a separate operational department with its own portable asset
and consumable custody. Center departments must not be stripped of fixed assets
for visits without a recorded custody transfer.
"""

from dataclasses import dataclass
from typing import Dict, Tuple

CATALOG_DEPARTMENTS: Tuple[str, ...] = (
    "hair",
    "makeup",
    "eyebrows",
    "lashes",
    "lips",
    "nails",
    "facial",
    "manicure_pedicure",
    "hair_removal",
    "massage",
    "relaxation_room",
    "celebration_room",
    "coffee_lounge",
    "tailoring",
)

ADDITIONAL_OPERATIONAL_DEPARTMENTS: Tuple[str, ...] = (
    "home_visits",
)

DEPARTMENT_SERVICE_EVIDENCE: Dict[str, Tuple[str, ...]] = {
    "hair": (
        "hair_styling", "hair_cutting", "blow_dry", "single_color_dye",
        "lightening_and_toner", "hot_treatments", "cold_treatments",
        "head_spa", "hair_extensions",
    ),
    "makeup": ("daily_makeup", "evening_makeup", "occasion_makeup", "bridal_makeup", "makeup_trial", "lash_application"),
    "eyebrows": ("brow_services",),
    "lashes": ("lash_extensions", "lash_cleaning", "lash_lift"),
    "lips": ("lip_services",),
    "nails": ("gel", "acrylic", "polygel", "nail_art_and_addons"),
    "facial": ("basic_facial", "therapeutic_facial", "device_based_facial", "advanced_facial", "facial_addons"),
    "manicure_pedicure": ("manicure", "pedicure", "hand_and_foot_treatments"),
    "hair_removal": ("wax_threading", "laser_hair_removal"),
    "massage": ("classic_massage", "specialized_massage", "targeted_massage"),
    "relaxation_room": ("room_session", "vip_room_session", "refreshments_and_addons"),
    "celebration_room": ("celebration_packages", "decor", "photography_options", "refreshments_and_addons"),
    "coffee_lounge": ("hot_beverages", "cold_beverages", "desserts", "pizza_and_snacks"),
    "tailoring": ("alterations", "daily_tailoring", "luxury_tailoring", "fabrics_and_additional_services"),
    "home_visits": ("portable_service_delivery",),
}

REQUIREMENT_CATEGORIES: Tuple[str, ...] = (
    "fixed_assets_and_equipment",
    "reusable_tools",
    "operating_materials",
    "single_use_consumables",
    "cleaning_and_disinfection",
    "safety_and_ppe",
    "storage_and_organization",
    "maintenance_requirements",
    "damage_and_replacement",
    "minimum_stock_and_reorder_point",
)

PRINTABLE_SETUP_FIELDS: Tuple[str, ...] = (
    "department_name",
    "department_lead",
    "responsible_employee",
    "location",
    "requirement_category",
    "item_name",
    "purpose_or_linked_service",
    "asset_or_stock_code",
    "unit",
    "setup_quantity",
    "minimum_quantity",
    "reorder_point",
    "preferred_supplier",
    "brand_or_specification_when_approved",
    "purchase_status",
    "condition",
    "maintenance_frequency",
    "last_maintenance",
    "next_maintenance",
    "damage_status",
    "replacement_required",
    "notes",
    "prepared_by",
    "reviewed_by",
    "approval",
)

HOME_VISIT_RULES: Tuple[str, ...] = (
    "home_visits_have_separate_portable_assets",
    "home_visits_have_separate_operating_stock",
    "home_visits_have_separate_consumable_stock",
    "home_visit_items_are_issued_under_employee_custody",
    "fixed_center_assets_are_not_removed_for_visits_by_default",
    "temporary_transfer_from_center_requires_recorded_custody_transfer",
    "visit_kit_is_checked_out_and_returned_per_shift_or_visit",
    "missing_damaged_or_consumed_items_are_reconciled_after_return",
)

REQUIREMENT_SOURCE_RULES: Tuple[str, ...] = (
    "catalog_service_scope_may_define_requirement_family",
    "exact_equipment_brand_quantity_or_specification_must_not_be_invented",
    "unverified_exact_items_remain_blank_until_setup_review",
    "purchase_invoice_or_verified_asset_record_may_confirm_exact_item",
    "department_lead_may_propose_exact_item_for_management_approval",
    "confirmed_item_becomes_canonical_department_requirement",
)

@dataclass(frozen=True)
class DepartmentRequirementsContract:
    one_requirements_register_per_department: bool = True
    printable_setup_register: bool = True
    assets_and_consumables_are_separated: bool = True
    maintenance_and_damage_are_part_of_same_program: bool = True
    reorder_points_supported: bool = True
    employee_custody_supported: bool = True
    home_visit_stock_is_independent: bool = True
    no_unverified_exact_items_are_invented: bool = True
    nada_operates_daily_tracking: bool = True
    ameer_monitors_exceptions_and_cross_department_patterns: bool = True


def requirements_contract() -> DepartmentRequirementsContract:
    return DepartmentRequirementsContract()
