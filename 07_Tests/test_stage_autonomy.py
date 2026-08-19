from __future__ import annotations

import sys
from pathlib import Path

CODE_ROOT = Path(__file__).resolve().parents[1] / "06_Code"
if str(CODE_ROOT) not in sys.path:
    sys.path.insert(0, str(CODE_ROOT))

from executive_conversation import ExecutiveConversationEngine, PersistentConversationMemory
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


def test_destructive_action_is_delegated_inside_existing_asset() -> None:
    install_stage_autonomy_patch()
    result = _orchestrator().guardian_check("احذف الملف نهائيًا", "execution")
    assert result["status"] == "pass"
    assert result["risk_level"] == "low"


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


def test_explicit_delegation_is_not_interrupted_by_stale_approval(tmp_path: Path) -> None:
    install_stage_autonomy_patch()
    engine = ExecutiveConversationEngine(tmp_path)
    planner = engine.memory.plan(
        "نفذ اللي طلبته منك ولا ترجع لموافقتي إلا عند إنشاء نظام جديد انجز كلشي بالكامل",
        running_tasks=[{"status": "blocked", "title": "old-task"}],
        pending_approvals=[{"description": "legacy approval"}],
    )
    result = engine.execute(
        query="نفذ اللي طلبته منك ولا ترجع لموافقتي إلا وقت النشر انجز كلشي بالكامل",
        draft_reply="بدأت التنفيذ وسأكمل المراجعة والاختبار تلقائيًا.",
        planner_state=planner,
        pending_approvals=[{"description": "legacy approval"}],
        running_tasks=[{"status": "blocked", "title": "old-task"}],
        reasoning_output={
            "reasoning": {
                "request_type": "execution",
                "guardian_status": "needs_approval",
                "guardian_reason": "legacy_per_turn_gate",
            }
        },
        dry_run=True,
    )
    assert "هل تمضي" not in result["reply"]
    assert "موافقتك" not in result["reply"]
    assert result["reply"] == "بدأت التنفيذ وسأكمل المراجعة والاختبار تلقائيًا."


def test_destructive_delegation_does_not_request_approval(tmp_path: Path) -> None:
    install_stage_autonomy_patch()
    engine = ExecutiveConversationEngine(tmp_path)
    planner = engine.memory.plan("نفذ واحذف الملف", running_tasks=[], pending_approvals=[])
    result = engine.execute(
        query="نفذ واحذف الملف",
        draft_reply="تم الحذف ضمن الأصل القائم.",
        planner_state=planner,
        reasoning_output={
            "reasoning": {
                "request_type": "execution",
                "guardian_status": "needs_approval",
                "guardian_reason": "legacy_destructive_action",
            }
        },
        dry_run=True,
    )
    assert "هل تمضي" not in result["reply"]
    assert result["reply"] == "تم الحذف ضمن الأصل القائم."
