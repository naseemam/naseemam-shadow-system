import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "06_Code"))

from kernel.intent_fidelity import enforce_request_type, explicit_execution_requested, preserve_scope


def test_start_is_execution_not_planning_by_default():
    result = enforce_request_type("ابدأ تنفيذ التعديل", "planning")
    assert result["effective_request_type"] == "execution"
    assert result["classifier_overridden"] is True


def test_continue_inherits_active_goal_as_execution():
    assert explicit_execution_requested("كمل", previous_goal="تعديل نظام الصلاحيات") is True
    result = enforce_request_type("كمل", "question", previous_goal="تعديل نظام الصلاحيات")
    assert result["effective_request_type"] == "execution"


def test_explicit_plan_request_stays_planning():
    result = enforce_request_type("أعطني خطة قبل أن نبدأ", "planning")
    assert result["effective_request_type"] == "planning"
    assert result["classifier_overridden"] is False


def test_edit_directive_cannot_be_demoted_to_analysis():
    result = enforce_request_type("عدّل الكود وأصلح المشكلة", "analysis")
    assert result["effective_request_type"] == "execution"


def test_execution_cannot_be_demoted_to_conversation_only():
    result = enforce_request_type("نفذ المهمة", "conversation_only")
    assert result["effective_request_type"] == "execution"


def test_scope_narrowing_is_reported_not_silently_accepted():
    result = preserve_scope(original_scope="execute_change", derived_scope="plan_only")
    assert result["valid"] is False
    assert result["violation"] == "narrow"
