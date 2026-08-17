from kernel.arabic_intent_lexicon import classify_arabic_intent


def test_friendly_greeting_is_conversation_only():
    result = classify_arabic_intent("مرحبا يا أمير، كيف حالك؟")
    assert result.intent == "conversation"
    assert result.route == "conversation"
    assert result.execution_candidate is False


def test_friendly_content_request_does_not_execute_code():
    result = classify_arabic_intent("اكتب لي رسالة ودية لصديقي")
    assert result.intent == "write"
    assert result.execution_candidate is False


def test_ui_improvement_is_explicit_write_candidate():
    result = classify_arabic_intent("ممكن تحسن واجهة المستخدم؟")
    assert result.intent == "write"
    assert result.execution_candidate is True


def test_read_and_extract_are_read_route():
    assert classify_arabic_intent("اقرأ ملف الإعدادات").route == "read"
    assert classify_arabic_intent("استخرج اسم المشروع").route == "read"


def test_plan_is_not_external_execution():
    result = classify_arabic_intent("حدد الخطوات وصمم خطة للعمل")
    assert result.intent == "plan"
    assert result.execution_candidate is False


def test_test_publish_and_approval_routes():
    assert classify_arabic_intent("شغل الاختبارات").route == "test"
    assert classify_arabic_intent("انشر على Railway").route == "publish"
    assert classify_arabic_intent("أوافق على النشر").route == "approval"
    assert classify_arabic_intent("انشر على Railway").requires_approval is True
