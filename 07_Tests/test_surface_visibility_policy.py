from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "06_Code"))

from kernel.surface_visibility_policy import authorize_surface, classify_path, public_navigation


def test_public_surfaces_are_explicit_only():
    assert authorize_surface("/hilm/store", "anonymous").allowed is True
    assert authorize_surface("/school/public/news", "anonymous").allowed is True
    assert authorize_surface("/trading", "anonymous").allowed is False
    assert authorize_surface("/admin", "customer").allowed is False


def test_unknown_future_surface_defaults_private():
    assert classify_path("/future-secret-module") == "private"
    assert authorize_surface("/future-secret-module", "anonymous").allowed is False


def test_cashier_only_gets_cashier_scope_not_trading_or_ameer_admin():
    assert authorize_surface("/hilm/pos", "cashier").allowed is True
    assert authorize_surface("/hilm/invoicing", "cashier").allowed is True
    assert authorize_surface("/trading", "cashier").allowed is False
    assert authorize_surface("/admin", "cashier").allowed is False


def test_staff_can_receive_explicit_private_scope():
    assert authorize_surface("/hilm/management", "staff").allowed is False
    assert authorize_surface("/hilm/management", "staff", staff_scopes=frozenset({"private"})).allowed is True


def test_founder_and_ameer_have_private_access():
    assert authorize_surface("/trading", "founder").allowed is True
    assert authorize_surface("/admin", "ameer").allowed is True


def test_public_navigation_does_not_leak_private_areas():
    nav = public_navigation()
    assert nav == ("hilm_public", "hilm_store", "school_public")
    assert "trading" not in nav
    assert "administration" not in nav
