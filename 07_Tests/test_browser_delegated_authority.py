import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "06_Code"))

from kernel.browser_authorization import BrowserAuthorizationGate


def test_navigate_is_authorized_without_founder_approval():
    with tempfile.TemporaryDirectory() as tmp:
        gate = BrowserAuthorizationGate(tmp)
        action = gate.propose_action("navigate", "https://example.com", "افتح الموقع", "يفتح الموقع")
        assert action.status == "authorized"
        assert action.requires_founder_approval is False


def test_read_is_authorized_without_founder_approval():
    with tempfile.TemporaryDirectory() as tmp:
        gate = BrowserAuthorizationGate(tmp)
        action = gate.propose_action("read", "dashboard", "اقرأ اللوحة", "تُقرأ البيانات")
        assert action.status == "authorized"


def test_fill_draft_form_is_authorized_without_founder_approval():
    with tempfile.TemporaryDirectory() as tmp:
        gate = BrowserAuthorizationGate(tmp)
        action = gate.propose_action(
            "fill", "payment-form", "حضّر بيانات الدفع", "تعبئة المسودة فقط",
            parameters={"operation": "payment", "actual_funds_movement": False},
        )
        assert action.status == "authorized"
        assert action.requires_founder_approval is False


def test_actual_funds_movement_is_pending_founder():
    with tempfile.TemporaryDirectory() as tmp:
        gate = BrowserAuthorizationGate(tmp)
        action = gate.propose_action(
            "click", "confirm-payment", "أكد التحويل", "تنفيذ الدفع",
            parameters={"operation": "transfer_funds", "actual_funds_movement": True, "amount": 100},
        )
        assert action.status == "pending_founder"
        assert action.requires_founder_approval is True
        assert action.sovereign_action == "transfer_funds"


def test_browser_gate_cannot_require_approval_for_ordinary_click():
    with tempfile.TemporaryDirectory() as tmp:
        gate = BrowserAuthorizationGate(tmp)
        assert gate.requires_approval_for_action("click", {"operation": "click"}) is False
