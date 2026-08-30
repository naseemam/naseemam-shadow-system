from kernel.autonomous_execution_loop import (
    EXECUTION_PHASES,
    decide_execution_step,
    external_resources_are_advisory,
    next_phase,
)
from kernel.conversation_realm import classify_realm, conversation_policy_snapshot


def test_routine_execution_is_autonomous():
    for action in ("edit_code", "run_tests", "deploy_existing_service", "publish_existing_site", "browse", "send_email"):
        decision = decide_execution_step(action)
        assert decision.may_execute is True
        assert decision.founder_approval_required is False
        assert decision.external_assistant_required is False


def test_execution_failure_loops_to_repair_not_approval():
    assert next_phase("test_result", success=False, outcome_complete=False) == "repair_if_needed"
    assert next_phase("repair_if_needed", success=True, outcome_complete=False) == "retest"
    assert next_phase("retest", success=False, outcome_complete=False) == "repair_if_needed"


def test_execution_loop_is_outcome_driven():
    assert EXECUTION_PHASES == (
        "understand_goal",
        "inspect_current_state",
        "choose_tools_and_steps",
        "execute_changes",
        "test_result",
        "repair_if_needed",
        "retest",
        "continue_until_complete",
    )
    assert next_phase("retest", success=True, outcome_complete=True) == "complete"


def test_chatgpt_manus_and_models_are_optional_resources_not_authorities():
    snapshot = external_resources_are_advisory(["ChatGPT", "Manus", "OpenAI", "provider-x"])
    assert snapshot["required_for_routine_execution"] is False
    assert snapshot["sovereign_authority"] is False
    assert snapshot["may_be_replaced"] is True
    assert snapshot["may_be_skipped"] is True


def test_friendly_chat_is_not_forced_into_work_pipeline():
    realm = classify_realm("اليوم ودي أسولف معك شوي", declared_room="ودية")
    assert realm.realm == "friendly"
    assert realm.work_pipeline_required is False
    assert realm.free_form_language is True


def test_work_request_inside_friendly_chat_can_execute_without_destroying_context():
    realm = classify_realm("طيب عدل الملف اللي كنا نشتغل عليه", declared_room="ودية")
    assert realm.realm == "work"
    assert realm.execution_requested is True
    assert realm.work_pipeline_required is True
    assert realm.free_form_language is True


def test_work_room_does_not_force_every_turn_into_execution():
    realm = classify_realm("وش رايك بالتصميم الحالي؟", declared_room="أعمال")
    assert realm.execution_requested is False
    assert realm.work_pipeline_required is False
    assert realm.free_form_language is True


def test_conversation_policy_does_not_constrain_speech_style():
    snapshot = conversation_policy_snapshot()
    assert snapshot["friendly_conversation_is_distinct_from_work"] is True
    assert snapshot["classification_is_not_a_speech_constraint"] is True
    assert snapshot["approval_requirements_come_only_from_sovereign_gates"] is True
