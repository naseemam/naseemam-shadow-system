import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "06_Code" / "kernel"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_management_program_is_administrative_ssot():
    mod = _load("hilm_management_ssot")
    contract = mod.management_ssot_contract()
    assert contract.management_program_is_administrative_ssot is True
    assert "services" in mod.MANAGEMENT_DOMAINS
    assert "products" in mod.MANAGEMENT_DOMAINS
    assert "employees" in mod.MANAGEMENT_DOMAINS
    assert "payroll" in mod.MANAGEMENT_DOMAINS
    assert "inventory" in mod.MANAGEMENT_DOMAINS
    assert "warehouses" in mod.MANAGEMENT_DOMAINS
    assert "invoices" in mod.MANAGEMENT_DOMAINS


def test_service_product_and_price_changes_sync_to_commerce_surfaces():
    mod = _load("hilm_management_ssot")
    contract = mod.management_ssot_contract()
    assert contract.price_changes_sync_to_storefront_cashier_cart_and_checkout is True
    assert contract.product_changes_sync_to_storefront_and_cashier is True
    assert contract.service_changes_sync_to_storefront_and_cashier is True
    assert "public_storefront" in mod.SYNC_TARGETS
    assert "shared_cart" in mod.SYNC_TARGETS
    assert "checkout_payment_gateway" in mod.SYNC_TARGETS
    assert "cashier_pos" in mod.SYNC_TARGETS


def test_paid_invoice_keeps_historical_price_and_unpaid_commerce_revalidates():
    mod = _load("hilm_management_ssot")
    contract = mod.management_ssot_contract()
    assert contract.historical_paid_invoices_keep_price_snapshots is True
    assert contract.unpaid_commerce_is_revalidated_after_price_change is True
    assert "existing_paid_invoice_keeps_historical_price_snapshot" in mod.PRICE_CHANGE_RULES
    assert "existing_unpaid_cart_or_booking_is_revalidated_before_payment" in mod.PRICE_CHANGE_RULES


def test_inventory_and_warehouses_drive_sellable_availability():
    mod = _load("hilm_management_ssot")
    contract = mod.management_ssot_contract()
    assert contract.inventory_and_warehouse_changes_sync_to_sellable_availability is True
    assert "storefront_availability_uses_canonical_sellable_stock" in mod.INVENTORY_SYNC_RULES
    assert "cashier_and_storefront_must_not_maintain_independent_stock_counts" in mod.INVENTORY_SYNC_RULES


def test_employee_payroll_and_internal_hr_data_remain_private():
    mod = _load("hilm_management_ssot")
    contract = mod.management_ssot_contract()
    visibility = mod.domain_visibility()
    assert contract.employee_and_payroll_data_remain_private_internal is True
    assert "payroll" in visibility["private_internal"]
    assert "employee_discounts_and_deductions" in visibility["private_internal"]
    assert "payroll" not in visibility["public_sync"]


def test_pos_is_projection_of_management_ssot():
    mod = _load("pos_invoicing_architecture")
    snapshot = mod.architecture_snapshot()
    assert snapshot["management_program_is_administrative_ssot"] is True
    assert snapshot["cashier_is_synchronized_projection_not_independent_master"] is True
    assert "warehouses" in snapshot["modules"]
    assert "payroll" in snapshot["modules"]
