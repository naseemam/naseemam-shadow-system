import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "06_Code"))

from kernel.interaction_mode import classify_interaction_mode, reconcile_classifier
from kernel.arabic_context import understand_arabic


def test_explicit_execution_is_not_downgraded_to_planning():
    result = reconcile_classifier("نفذ التعديل على المستودع", "planning")
    assert result["effective_mode"] == "execution"
    assert result["classifier_overridden"] is True
    assert result["semantic_authority"] == "founder_directive"


def test_continue_inherits_active_goal_as_execution():
    mode = classify_interaction_mode("كمل", previous_goal="مراجعة المستودع وتعديل الحوكمة")
    assert mode.mode == "continuation"
    assert mode.execution_requested is True


def test_correction_is_execution_not_analysis_only():
    result = reconcile_classifier("مو كذا صلحها", "analysis")
    assert result["effective_mode"] == "correction"
    assert result["execution_requested"] is True


def test_explicit_plan_request_remains_planning():
    mode = classify_interaction_mode("عطني خطة لتطوير النظام")
    assert mode.mode == "planning"
    assert mode.execution_requested is False


def test_explicit_suggestion_remains_suggestion():
    mode = classify_interaction_mode("وش تقترح نعدل في الواجهة")
    assert mode.mode == "suggestion"
    assert mode.execution_requested is False


def test_classifier_cannot_manufacture_execution_from_plan_only_request():
    result = reconcile_classifier("عطني خطة فقط", "execution")
    assert result["effective_mode"] == "planning"
    assert result["classifier_overridden"] is True


def test_arabic_context_carries_interaction_mode_and_original_directive():
    understood = understand_arabic("كمل", previous_goal="إصلاح صلاحيات أمير")
    assert understood.founder_directive is not None
    assert understood.founder_directive.original_text == "كمل"
    assert understood.interaction_mode is not None
    assert understood.interaction_mode.mode == "continuation"
