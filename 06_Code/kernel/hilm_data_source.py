"""Canonical Hilm Alnada business data source."""

CANONICAL_ENTITIES = (
    "services",
    "service_prices",
    "bookings",
    "customers",
    "employees",
    "inventory_items",
    "inventory_movements",
    "sales",
    "sale_lines",
    "payments",
    "offers",
)


def data_source_policy():
    return {
        "mode": "single_source_of_truth",
        "entities": list(CANONICAL_ENTITIES),
        "owner": "ameer_platform",
        "all_systems_share_same_state": True,
        "analytics_read_same_state": True,
        "pos_reads_same_state": True,
        "booking_reads_same_state": True,
        "store_reads_same_state": True,
        "derived_views_are_not_authoritative": True,
        "mutations_are_audited": True,
    }
