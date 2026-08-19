from pathlib import Path

from kernel.shadow_foundation import ShadowFoundation


def test_shadow_foundation_seeds_platform_projects_and_sites(tmp_path: Path):
    foundation = ShadowFoundation(tmp_path)
    projects = {row["project_id"]: row for row in foundation.list_projects()}

    assert projects["shadow"]["kind"] == "platform"
    assert projects["dream_al_nada"]["parent_id"] == "shadow"
    assert projects["school"]["parent_id"] == "shadow"
    assert projects["trading"]["parent_id"] == "shadow"
    assert projects["dream_al_nada_store"]["parent_id"] == "dream_al_nada"
    assert projects["dream_al_nada_admin"]["parent_id"] == "dream_al_nada"


def test_founder_and_ameer_are_global_assignments(tmp_path: Path):
    foundation = ShadowFoundation(tmp_path)

    assert any(a["subject_id"] == "founder" and a["role_id"] == "founder" for a in foundation.assignments())
    assert any(a["subject_id"] == "ameer" and a["role_id"] == "ameer" for a in foundation.assignments())


def test_trading_execution_is_delegated_to_ameer(tmp_path: Path):
    foundation = ShadowFoundation(tmp_path)

    decision = foundation.can("ameer", "ameer", "trading", "trading.execute", "external_effect")

    assert decision["allowed"] is True
    assert decision["reason"] == "allowed"
    assert decision["approval"] == "ameer_policy"
    assert foundation.snapshot()["trading_execution_default"] == "ameer_delegated"


def test_customer_is_limited_to_public_store_scope(tmp_path: Path):
    foundation = ShadowFoundation(tmp_path)
    foundation.assign("customer-1", "customer", "dream_al_nada_store")

    public_read = foundation.can("customer-1", "customer", "dream_al_nada_store", "project.read", "read")
    admin_read = foundation.can("customer-1", "customer", "dream_al_nada_admin", "project.read", "read")

    assert public_read["allowed"] is True
    assert admin_read["allowed"] is False
    assert admin_read["reason"] == "no_project_assignment"
