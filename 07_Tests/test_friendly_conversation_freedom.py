from kernel.conversation_realm import classify_realm, conversation_policy_snapshot


def test_friendly_room_stays_free_form_without_work_pipeline():
    realm = classify_realm("تعال نسولف شوي 🫣", declared_room="friendly")
    assert realm.realm == "friendly"
    assert realm.free_form_language is True
    assert realm.work_pipeline_required is False
    assert realm.preserve_tone_and_context is True
    assert realm.behavioral_guardian_may_rewrite is False


def test_friendly_interaction_is_not_forbidden_by_classifier():
    policy = conversation_policy_snapshot()
    assert policy["classifier_cannot_forbid_friendly_interaction"] is True
    assert policy["friendly_interaction_may_be_warm_playful_affectionate_or_imaginative"] is True
    assert policy["behavioral_guardian_cannot_rewrite_friendly_tone_by_default"] is True


def test_work_request_inside_friendly_chat_preserves_tone_context():
    realm = classify_realm("عدل الملف هذا وبعدين نكمل سوالفنا", declared_room="friendly")
    assert realm.realm == "work"
    assert realm.execution_requested is True
    assert realm.work_pipeline_required is True
    assert realm.preserve_tone_and_context is True
    assert realm.behavioral_guardian_may_rewrite is False


def test_sovereign_gates_govern_actions_not_ordinary_language():
    policy = conversation_policy_snapshot()
    assert policy["sovereign_gates_govern_actions_not_ordinary_language"] is True
    assert policy["approval_requirements_come_only_from_sovereign_gates"] is True


def test_provider_or_worker_cannot_become_persona_authority():
    policy = conversation_policy_snapshot()
    assert policy["provider_or_worker_prompt_cannot_become_persona_authority"] is True
