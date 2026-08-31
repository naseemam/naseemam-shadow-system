"""Separate operational inventory and storekeeping for Hilm Alnada service delivery.

Retail/store inventory is distinct from internal operational consumables used by
service providers. This module models custody, receiving, issuing, returns, waste,
manual paper receipts, scanned/photo evidence, and later reconciliation during
stock count and costing.
"""

from dataclasses import dataclass
from typing import Tuple


INVENTORY_DOMAINS: Tuple[str, ...] = (
    "retail_inventory_for_customer_sale",
    "operational_inventory_for_service_delivery",
)

OPERATIONAL_STOCK_ITEM_FIELDS: Tuple[str, ...] = (
    "item_id",
    "item_name",
    "category",
    "unit",
    "brand",
    "shade_or_variant_when_applicable",
    "batch_number_when_applicable",
    "expiry_date_when_applicable",
    "quantity_on_hand",
    "reorder_level",
    "storage_location",
    "average_cost",
    "last_cost",
    "supplier_id",
)

OPERATIONAL_STOCK_MOVEMENT_TYPES: Tuple[str, ...] = (
    "supplier_receipt",
    "issue_to_service_provider",
    "return_from_service_provider",
    "transfer_between_storage_locations",
    "waste_or_damage",
    "stock_count_adjustment",
)

STOREKEEPER_RECEIVING_FLOW: Tuple[str, ...] = (
    "storekeeper_receives_goods_from_supplier_or_internal_transfer",
    "create_receiving_record",
    "record_supplier_and_invoice_reference",
    "record_item_quantity_unit_batch_and_expiry_when_applicable",
    "attach_or_scan_supplier_invoice_or_delivery_note",
    "validate_received_quantity_against_document",
    "post_stock_increase",
    "retain_original_document_image_for_audit",
)

SERVICE_PROVIDER_ISSUE_FLOW: Tuple[str, ...] = (
    "service_provider_requests_operational_material",
    "storekeeper_selects_employee_and_related_service_or_work_order_when_known",
    "record_item_and_quantity_issued",
    "generate_numbered_issue_receipt",
    "storekeeper_hands_material_to_service_provider",
    "service_provider_acknowledges_receipt_on_paper_or_digitally",
    "attach_or_scan_signed_paper_issue_receipt_when_used",
    "post_stock_decrease",
    "link_issue_to_employee_service_and_cost_center",
)

MANUAL_DOCUMENT_CAPTURE_FLOW: Tuple[str, ...] = (
    "capture_photo_or_scan_of_receipt_invoice_or_delivery_note",
    "retain_original_image_as_audit_attachment",
    "extract_candidate_fields_when_supported",
    "mark_extracted_values_as_unverified_draft",
    "show_source_image_beside_structured_fields",
    "flag_low_confidence_or_ambiguous_values",
    "authorized_employee_reviews_and_confirms",
    "post_confirmed_inventory_transaction",
)

ISSUE_RECEIPT_FIELDS: Tuple[str, ...] = (
    "issue_receipt_number",
    "issued_at",
    "storekeeper_employee_id",
    "receiving_service_provider_employee_id",
    "department_or_service_area",
    "service_booking_or_work_order_id_when_known",
    "item_id",
    "item_name",
    "quantity",
    "unit",
    "batch_or_expiry_when_relevant",
    "purpose_or_service_notes",
    "receiver_acknowledgement",
    "paper_receipt_attachment",
)

RECEIVING_DOCUMENT_FIELDS: Tuple[str, ...] = (
    "receiving_number",
    "received_at",
    "storekeeper_employee_id",
    "supplier_id",
    "supplier_invoice_number",
    "supplier_delivery_note_number",
    "items",
    "quantities",
    "units",
    "batch_numbers_when_applicable",
    "expiry_dates_when_applicable",
    "invoice_attachment",
    "delivery_note_attachment",
)

STOCK_COUNT_AND_RECONCILIATION: Tuple[str, ...] = (
    "freeze_or_timestamp_count_scope",
    "count_physical_stock_by_location",
    "compare_physical_count_with_ledger",
    "trace_supplier_receipts",
    "trace_employee_issue_receipts",
    "trace_returns_waste_and_adjustments",
    "show_unmatched_or_unconfirmed_documents",
    "calculate_variance_quantity_and_value",
    "record_reason_and_authorized_adjustment",
    "retain_reconciliation_audit_trail",
)

ERROR_PREVENTION_RULES: Tuple[str, ...] = (
    "retail_and_operational_inventory_ledgers_must_not_be_merged",
    "every_stock_movement_has_unique_number_and_timestamp",
    "employee_issue_is_linked_to_named_receiver",
    "paper_scan_or_photo_does_not_post_stock_without_confirmation",
    "original_document_image_is_retained",
    "structured_quantity_and_unit_fields_are_used_instead_of_free_text_when_possible",
    "batch_and_expiry_are_recorded_for_applicable_products",
    "negative_stock_requires_explicit exception handling and audit",
)


@dataclass(frozen=True)
class OperationalInventoryContract:
    retail_and_operational_inventory_are_separate: bool = True
    operational_inventory_has_storekeeper_custody: bool = True
    provider_issue_requires_numbered_receipt: bool = True
    provider_receipt_can_be_paper_or_digital: bool = True
    paper_issue_receipts_can_be_scanned_or_photographed: bool = True
    supplier_receipts_and_invoices_can_be_scanned_or_photographed: bool = True
    scanned_data_is_draft_until_confirmed: bool = True
    original_images_are_retained_for_audit: bool = True
    movements_support_returns_waste_and_adjustments: bool = True
    stock_count_reconciles_against_receiving_and_issue_documents: bool = True
    movement_can_link_to_employee_and_service: bool = True
    batch_and_expiry_supported_when_applicable: bool = True


def operational_inventory_contract() -> OperationalInventoryContract:
    return OperationalInventoryContract()
