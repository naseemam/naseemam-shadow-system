import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "06_Code"))

from kernel.approval_gate import ApprovalGate
from kernel.execution_boundary import _HIGH_RISK_ACTIONS_REQUIRING_APPROVAL


def test_internal_repository_actions_are_not_founder_gate_actions():
    assert "delete" not in _HIGH_RISK_ACTIONS_REQUIRING_APPROVAL
    assert "merge" not in _HIGH_RISK_ACTIONS_REQUIRING_APPROVAL
    assert "publish" in _HIGH_RISK_ACTIONS_REQUIRING_APPROVAL
    assert "deploy" in _HIGH_RISK_ACTIONS_REQUIRING_APPROVAL


def test_approval_gate_is_limited_to_publish_external_financial():
    assert "publish" in ApprovalGate.HIGH_RISK_ACTIONS
    assert "deploy" in ApprovalGate.HIGH_RISK_ACTIONS
    assert "external" in ApprovalGate.HIGH_RISK_ACTIONS
    assert "financial" in ApprovalGate.HIGH_RISK_ACTIONS
    assert "delete" not in ApprovalGate.HIGH_RISK_ACTIONS


def test_deploy_is_a_valid_founder_gate_action():
    assert "deploy" in ApprovalGate.VALID_ACTIONS
