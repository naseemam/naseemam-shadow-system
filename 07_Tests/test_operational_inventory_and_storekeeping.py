import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "06_Code" / "kernel"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_retail_and_operational_inventory_are_separate():
    mod = _load("operational_inventory_and_storekeeping")
    contract = mod.operational_inventory_contract()
    assert contract.retail_and_operational_inventory_are_separate is True
    assert "retail_inventory_for_customer_sale" in mod.INVENTORY_DOMAINS
    assert "operational_inventory_for_service_delivery" in mod.INVENTORY_DOMAINS


def test_service_provider_issue_requires_storekeeper_receipt_and_named_receiver():
    mod = _load("operational_inventory_and_storekeeping")
    contract = mod.operational_inventory_contract()
    assert contract.operational_inventory_has_storekeeper_custody is True
    assert contract.provider_issue_requires_numbered_receipt is True
    assert "receiving_service_provider_employee_id" in mod.ISSUE_RECEIPT_FIELDS
    assert "generate_numbered_issue_receipt" in mod.SERVICE_PROVIDER_ISSUE_FLOW
    assert "post_stock_decrease" in mod.SERVICE_PROVIDER_ISSUE_FLOW


def test_paper_receipts_and_supplier_invoices_can_be_scanned_safely():
    mod = _load("operational_inventory_and_storekeeping")
    contract = mod.operational_inventory_contract()
    assert contract.paper_issue_receipts_can_be_scanned_or_photographed is True
    assert contract.supplier_receipts_and_invoices_can_be_scanned_or_photographed is True
    assert contract.scanned_data_is_draft_until_confirmed is True
    assert contract.original_images_are_retained_for_audit is True
    assert "mark_extracted_values_as_unverified_draft" in mod.MANUAL_DOCUMENT_CAPTURE_FLOW
    assert "authorized_employee_reviews_and_confirms" in mod.MANUAL_DOCUMENT_CAPTURE_FLOW


def test_stock_count_traces_receipts_issues_returns_and_waste():
    mod = _load("operational_inventory_and_storekeeping")
    contract = mod.operational_inventory_contract()
    assert contract.stock_count_reconciles_against_receiving_and_issue_documents is True
    assert contract.movements_support_returns_waste_and_adjustments is True
    assert "trace_supplier_receipts" in mod.STOCK_COUNT_AND_RECONCILIATION
    assert "trace_employee_issue_receipts" in mod.STOCK_COUNT_AND_RECONCILIATION
    assert "trace_returns_waste_and_adjustments" in mod.STOCK_COUNT_AND_RECONCILIATION


def test_batches_expiry_and_service_cost_linkage_are_supported():
    mod = _load("operational_inventory_and_storekeeping")
    contract = mod.operational_inventory_contract()
    assert contract.movement_can_link_to_employee_and_service is True
    assert contract.batch_and_expiry_supported_when_applicable is True
    assert "batch_number_when_applicable" in mod.OPERATIONAL_STOCK_ITEM_FIELDS
    assert "expiry_date_when_applicable" in mod.OPERATIONAL_STOCK_ITEM_FIELDS
