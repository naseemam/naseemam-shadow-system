import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "06_Code"))

from kernel.ameer_authority import (
    canonical_sovereign_action,
    requires_founder_approval,
)
from kernel.capability_registry import CapabilityRegistry
from kernel.execution_authorization import ExecutionAuthorization
from kernel.permission_registry import PermissionRegistry


def test_only_three_sovereign_gate_categories_exist():
    assert requires_founder_approval("create_site", {}) is True
    assert requires_founder_approval(
        "publish", {"new_root_asset": True, "final_release": True}
    ) is True
    assert requires_founder_approval("transfer_funds", {"amount": 1}) is True


def test_component_creation_inside_existing_asset_is_autonomous():
    assert canonical_sovereign_action(
        "create_site", {"existing_asset": True, "creation_scope": "component"}
    ) is None


def test_existing_asset_operations_are_autonomous():
    for action in (
        "deploy",
        "publish",
        "rollback",
        "delete",
        "merge",
        "email.send",
        "provider.replace",
        "connector.replace",
        "worker.create",
        "self_modify",
    ):
        assert requires_founder_approval(action, {"existing_asset": True}) is False


def test_quotes_and_payment_preparation_do_not_move_money():
    assert requires_founder_approval(
        "payment", {"actual_funds_movement": False, "mode": "prepare"}
    ) is False


def test_permission_cards_default_to_delegated_granted():
    with tempfile.TemporaryDirectory() as tmp:
        registry = PermissionRegistry(tmp)
        registry.ensure("example-capability")
        card = registry.get_for_capability("example-capability")
        assert card is not None
        assert card["permission_status"] == "granted"
        assert card["enabled"] is True
        assert registry.is_permitted("example-capability") is True


def test_legacy_requires_approval_cannot_create_new_founder_gate():
    with tempfile.TemporaryDirectory() as tmp:
        registry = PermissionRegistry(tmp)
        registry.set_requires_approval("example-capability")
        card = registry.get_for_capability("example-capability")
        assert card is not None
        assert card["permission_status"] == "granted"
        assert registry.is_permitted("example-capability") is True


def _registered_execution_stack(tmp: str, name: str = "autonomy_test"):
    caps = CapabilityRegistry(tmp)
    cap_id = caps.register(
        name=name,
        description="Autonomy regression capability",
        scope="test",
        approved_by="founder",
        status="extended",
    )
    perms = PermissionRegistry(tmp)
    auth = ExecutionAuthorization(tmp, caps, perms)
    return cap_id, perms, auth


def test_execution_authorization_auto_enables_registered_operational_capability():
    with tempfile.TemporaryDirectory() as tmp:
        _, _, auth = _registered_execution_stack(tmp)
        result = auth.check("autonomy_test", "self_modify", {"existing_asset": True})
        assert result["status"] == "approved"


def test_execution_authorization_pending_only_for_sovereign_gate():
    with tempfile.TemporaryDirectory() as tmp:
        _, _, auth = _registered_execution_stack(tmp)
        ordinary = auth.check("autonomy_test", "deploy", {"existing_asset": True})
        sovereign = auth.check("autonomy_test", "transfer_funds", {"amount": 100})
        assert ordinary["status"] == "approved"
        assert sovereign["status"] == "pending"
        assert sovereign["sovereign_action"] == "transfer_funds"


def test_legacy_permission_approval_flag_does_not_block_ordinary_execution():
    with tempfile.TemporaryDirectory() as tmp:
        cap_id, perms, auth = _registered_execution_stack(tmp)
        perms.set_requires_approval(cap_id)
        result = auth.check("autonomy_test", "deploy", {"existing_asset": True})
        assert result["status"] == "approved"


def test_ameer_can_write_inside_own_repository_not_only_runtime_workspace():
    with tempfile.TemporaryDirectory() as tmp:
        caps = CapabilityRegistry(tmp)
        perms = PermissionRegistry(tmp)
        auth = ExecutionAuthorization(tmp, caps, perms)
        result = auth.check(
            "file_operations",
            "write",
            {"tool_name": "file.create", "target": "06_Code/kernel/self_patch.py"},
        )
        assert result["status"] == "approved"


def test_file_write_cannot_escape_repository_boundary():
    with tempfile.TemporaryDirectory() as tmp:
        caps = CapabilityRegistry(tmp)
        perms = PermissionRegistry(tmp)
        auth = ExecutionAuthorization(tmp, caps, perms)
        result = auth.check(
            "file_operations",
            "write",
            {"tool_name": "file.create", "target": "../outside.txt"},
        )
        assert result["status"] == "denied"
