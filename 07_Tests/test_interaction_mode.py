from kernel.interaction_mode import classify_interaction_mode, reconcile_classifier


def test_execute_language_cannot_be_downgraded_to_planning():
    result = reconcile_classifier("نفذ التعديل الآن", "planning")
    assert result["effective_mode"] == "execution"
    assert result["classifier_overridden"] is True
    assert result["execution_requested"] is True


def test_continue_inherits_active_goal_as_execution():
    mode = classify_interaction_mode("كمل", previous_goal="تعديل المستودع واختبار النتيجة")
    assert mode.mode == "continuation"
    assert mode.execution_requested is True


def test_correction_is_executive_not_analysis_only():
    result = reconcile_classifier("مو كذا صلحها", "analysis")
    assert result["effective_mode"] == "correction"
    assert result["execution_requested"] is True


def test_explicit_plan_request_stays_planning():
    result = reconcile_classifier("عطني خطة للتعديل", "execution")
    assert result["effective_mode"] == "planning"
    assert result["execution_requested"] is False


def test_explicit_suggestion_stays_suggestion():
    result = reconcile_classifier("وش تقترح للتصميم؟", "execution")
    assert result["effective_mode"] == "suggestion"
    assert result["execution_requested"] is False


def test_classification_never_restricts_ameer_speech_style():
    result = reconcile_classifier("خلنا نسولف شوي", "conversation")
    assert result["speech_style_restricted"] is False
    assert result["friendly_conversation_may_remain_free_form"] is True
