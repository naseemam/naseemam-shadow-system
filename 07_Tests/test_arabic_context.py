from kernel.arabic_context import understand_arabic


def test_short_continuation_inherits_active_goal():
    result = understand_arabic("كمل", previous_goal="بناء الصفحة الرئيسية وربط الأزرار")
    assert result.continuation is True
    assert "بناء الصفحة الرئيسية" in result.canonical_command


def test_saudi_execution_shorthand():
    result = understand_arabic("سوها", previous_goal="إصلاح صندوق الدردشة")
    assert result.continuation is True
    assert result.canonical_command.startswith("نفذها")


def test_colloquial_failure_means_review_and_fix():
    result = understand_arabic("م ضبط", previous_goal="ربط زر الحجوزات")
    assert result.correction is True
    assert "أصلحها ذاتيًا" in result.canonical_command
    assert "ربط زر الحجوزات" in result.canonical_command


def test_context_reference_is_preserved():
    result = understand_arabic("الثاني")
    assert result.reference == "العنصر الثاني من السياق"


def test_fusha_is_not_needlessly_rewritten():
    text = "راجع المشروع واختبر الواجهة ثم أصلح الأخطاء"
    result = understand_arabic(text)
    assert result.canonical_command == text
