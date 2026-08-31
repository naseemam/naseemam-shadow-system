import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "06_Code"))

from kernel.ameer_authority import approval_actions, requires_founder_approval
from kernel.approval_gate import ApprovalGate
from kernel.execution_boundary import _HIGH_RISK_ACTIONS_REQUIRING_APPROVAL


def test_only_central_sovereign_actions_are_founder_gates():
    assert _HIGH_RISK_ACTIONS_REQUIRING_APPROVAL == set(approval_actions())
    assert "create_site" in _HIGH_RISK_ACTIONS_REQUIRING_APPROVAL
    assert "final_publish_new_asset" in _HIGH_RISK_ACTIONS_REQUIRING_APPROVAL
    assert "financial_commitment" in _HIGH_RISK_ACTIONS_REQUIRING_APPROVAL
    for action in ("delete", "merge", "publish", "deploy", "rollback", "email.send", "trading.execute"):
        assert action not in _HIGH_RISK_ACTIONS_REQUIRING_APPROVAL


def test_approval_gate_matches_central_authority():
    assert ApprovalGate.HIGH_RISK_ACTIONS == set(approval_actions())
    for action in ("delete", "publish", "deploy", "rollback", "external", "financial"):
        assert action not in ApprovalGate.HIGH_RISK_ACTIONS


def test_existing_asset_publish_is_autonomous_but_new_asset_final_release_is_not():
    assert requires_founder_approval("publish", {"existing_asset": True}) is False
    assert requires_founder_approval(
        "publish", {"new_root_asset": True, "final_release": True, "asset_id": "site-1"}
    ) is True


def test_actual_funds_movement_is_sovereign_gate():
    assert requires_founder_approval("transfer_funds", {"amount": 100}) is True
    assert requires_founder_approval("payment", {"actual_funds_movement": False}) is False


def test_legacy_actions_remain_valid_for_audit_but_do_not_gate_execution():
    assert "deploy" in ApprovalGate.VALID_ACTIONS
    for action in approval_actions():
        assert action in ApprovalGate.VALID_ACTIONS