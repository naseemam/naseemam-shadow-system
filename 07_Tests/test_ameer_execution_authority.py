import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "06_Code"))

from kernel.ameer_authority import approval_actions
from kernel.approval_gate import ApprovalGate
from kernel.execution_boundary import _HIGH_RISK_ACTIONS_REQUIRING_APPROVAL


def test_only_new_root_assets_are_founder_gate_actions():
    assert _HIGH_RISK_ACTIONS_REQUIRING_APPROVAL == set(approval_actions())
    for action in ("delete", "merge", "publish", "deploy", "rollback", "email.send", "trading.execute"):
        assert action not in _HIGH_RISK_ACTIONS_REQUIRING_APPROVAL


def test_approval_gate_is_limited_to_new_root_asset_creation():
    assert ApprovalGate.HIGH_RISK_ACTIONS == set(approval_actions())
    for action in ("delete", "publish", "deploy", "rollback", "external", "financial"):
        assert action not in ApprovalGate.HIGH_RISK_ACTIONS


def test_legacy_actions_remain_valid_for_audit_but_do_not_gate_execution():
    assert "deploy" in ApprovalGate.VALID_ACTIONS
    for action in approval_actions():
        assert action in ApprovalGate.VALID_ACTIONS
