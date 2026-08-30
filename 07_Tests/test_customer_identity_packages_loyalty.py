from importlib import import_module

module = import_module("06_Code.kernel.customer_identity_packages_loyalty")


def test_customer_registration_syncs_to_pos_and_management():
    contract = module.customer_commerce_contract()
    assert contract.registration_required_for_account_bound_purchase is True
    assert contract.automatic_profile_sync_to_pos is True
    assert contract.automatic_booking_sync_to_pos is True
    assert contract.automatic_order_sync_to_pos is True
    assert "website_registration_creates_customer_profile" in module.CUSTOMER_PROFILE_SYNC
    assert "pos_reads_same_customer_profile" in module.CUSTOMER_PROFILE_SYNC


def test_packages_support_self_gift_and_code_redemption():
    required = {
        "fixed_price_packages",
        "book_package_for_self",
        "buy_package_as_gift",
        "buy_package_for_another_customer",
        "generate_unique_redemption_code",
        "show_code_in_pos",
        "redeem_code_at_reception",
    }
    assert required.issubset(set(module.PACKAGE_CAPABILITIES))


def test_loyalty_is_part_of_shared_customer_profile():
    required = {
        "loyalty_account_per_customer",
        "earn_points_from_eligible_sales",
        "redeem_points_on_eligible_purchase",
        "show_balance_in_customer_account",
        "show_balance_in_pos",
        "show_history_in_management_system",
    }
    assert required.issubset(set(module.LOYALTY_CAPABILITIES))


def test_ameer_manages_offer_section_without_manual_founder_entry():
    contract = module.customer_commerce_contract()
    assert contract.offer_section_is_ameer_managed is True
    assert "ameer_may_change_offer_name" in module.OFFER_SECTION_CAPABILITIES
    assert "ameer_may_change_offer_price" in module.OFFER_SECTION_CAPABILITIES
    assert "founder_manual_entry_not_required" in module.OFFER_SECTION_CAPABILITIES
