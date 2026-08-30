from kernel.conversation_prompt_policy import prompt_behavior_for, prompt_policy_snapshot
from kernel.conversation_realm import classify_realm


def test_friendly_prompt_does_not_force_executive_closer():
    realm = classify_realm("تعال نسولف شوي 🫣", declared_room="friendly")
    behavior = prompt_behavior_for(realm)
    assert behavior.realm == "friendly"
    assert behavior.require_executive_tone is False
    assert behavior.require_next_step_closer is False
    assert behavior.require_question_closer is False


def test_friendly_prompt_preserves_warmth_and_playfulness():
    realm = classify_realm("هههه تعال هنا", declared_room="friendly")
    behavior = prompt_behavior_for(realm)
    assert behavior.preserve_warmth_and_playfulness is True
    assert behavior.preserve_contextual_style is True
    assert behavior.provider_may_override_persona is False


def test_work_request_inside_friendly_context_preserves_context():
    realm = classify_realm("عدل الملف وبعدها نكمل سوالفنا", declared_room="friendly")
    behavior = prompt_behavior_for(realm)
    assert behavior.realm == "work"
    assert behavior.require_operational_summary is True
    assert behavior.preserve_contextual_style is True
    assert behavior.preserve_warmth_and_playfulness is True


def test_global_work_prompt_cannot_control_friendly_chat():
    policy = prompt_policy_snapshot()
    assert policy["one_global_prompt_may_not_force_work_style_on_friendly_chat"] is True
    assert policy["friendly_chat_requires_no_next_step_closer"] is True
    assert policy["friendly_chat_requires_no_question_closer"] is True
    assert policy["friendly_chat_requires_no_formal_tone"] is True
