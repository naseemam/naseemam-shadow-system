import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "06_Code"))

from kernel.arabic_context import understand_arabic
from kernel.founder_directive import create_directive, execution_payload, validate_interpretation


def test_original_founder_wording_remains_semantic_authority():
    understanding = understand_arabic("كمل", previous_goal="انقل نواة أمير إلى بيئة جديدة بعد الموافقة")
    assert understanding.founder_directive is not None
    directive = understanding.founder_directive
    assert directive.original_text == "كمل"
    assert directive.semantic_authority == "original_text"
    assert "انقل نواة أمير" in directive.derived_text


def test_canonical_command_is_derived_not_replacement():
    understanding = understand_arabic("سوي", previous_goal="اختبر النسخة الجديدة")
    directive = understanding.founder_directive
    assert directive is not None
    assert directive.original_text == "سوي"
    assert understanding.canonical_command == directive.derived_text
    assert directive.as_context()["founder_directive"] == "سوي"


def test_execution_payload_always_carries_original_and_derived_text():
    directive = create_directive("عدلها", derived_text="عدّلها. استمر في الهدف الحالي: واجهة المدرسة")
    payload = execution_payload(directive, intent="code_edit")
    assert payload["founder_directive"] == "عدلها"
    assert payload["derived_interpretation"].startswith("عدّلها")
    assert payload["semantic_authority"] == "original_text"
    assert payload["intent"] == "code_edit"


def test_declared_narrowing_is_rejected():
    directive = create_directive("نفذ الترحيل كاملًا", derived_text="حضّر خطة ترحيل فقط")
    result = validate_interpretation(directive, transformation_types=["narrow"])
    assert result["valid"] is False
    assert "narrow" in result["violations"]


def test_silent_redirect_is_rejected():
    directive = create_directive("عدّل موقع المدرسة", derived_text="اكتب تقريرًا عن موقع المدرسة")
    result = validate_interpretation(directive, transformation_types=["redirect"])
    assert result["valid"] is False
    assert "redirect" in result["violations"]


def test_subsystem_cannot_add_founder_approval_requirement():
    directive = create_directive("عدّل الصفحة الحالية")
    result = validate_interpretation(directive, added_approval_requirement=True)
    assert result["valid"] is False
    assert "add_approval_gate" in result["violations"]


def test_assistant_or_provider_cannot_become_semantic_authority():
    directive = create_directive("نفذ المهمة", source="founder")
    payload = execution_payload(directive, interpreted_by="external_assistant")
    assert payload["semantic_authority"] == "original_text"
    assert payload["source"] == "founder"
    assert payload["interpreted_by"] == "external_assistant"
