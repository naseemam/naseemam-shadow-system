from __future__ import annotations

import sys
from pathlib import Path

CODE_ROOT = Path(__file__).resolve().parents[1] / "06_Code"
if str(CODE_ROOT) not in sys.path:
    sys.path.insert(0, str(CODE_ROOT))

from executive_conversation import PersistentConversationMemory
from kernel.stage_autonomy_patch import install_stage_autonomy_patch
from reasoning_orchestrator import AmeerOrchestrator


def _orchestrator() -> AmeerOrchestrator:
    return AmeerOrchestrator(
        documents=[],
        score_fn=lambda _q, _t: 0,
        normalize_fn=lambda text: text,
    )


def test_generic_execution_does_not_request_step_approval() -> None:
    install_stage_autonomy_patch()
    result = _orchestrator().guardian_check("نفّذ التعديل الآن ثم اختبره", "execution")
    assert result["status"] == "pass"
    assert result["risk_level"] == "low"


def test_destructive_action_remains_guarded() -> None:
    install_stage_autonomy_patch()
    result = _orchestrator().guardian_check("احذف الملف نهائيًا", "execution")
    assert result["status"] == "needs_approval"
    assert result["risk_level"] == "high"


def test_same_stage_continuation_ignores_stale_blocked_task(tmp_path: Path) -> None:
    install_stage_autonomy_patch()
    memory = PersistentConversationMemory(tmp_path)
    state = memory.plan(
        "اختبر التعديلات الحالية وكمل",
        running_tasks=[{"status": "blocked", "title": "old-stage-task"}],
        pending_approvals=[],
    )
    assert not any("مهام مفتوحة" in risk for risk in (state.risks or []))
    assert state.next_executive_action == "أكمل على هذا."
