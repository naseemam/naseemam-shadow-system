from kernel.execution_visibility import execution_visibility_policy
from kernel.resilience_and_recovery import resilience_policy
from kernel.self_development import self_development_policy


def test_skills_are_open_ended_and_can_be_researched_on_web():
    policy = self_development_policy()
    assert policy["skills_are_open_ended"] is True
    assert policy["web_research_for_new_skills"] is True
    assert policy["automatic_capability_registration_after_successful_validation"] is True
    assert policy["founder_not_required_for_routine_skill_acquisition"] is True


def test_execution_is_visible_without_exposing_secrets_or_private_reasoning():
    policy = execution_visibility_policy()
    assert policy["silent_black_box_execution"] is False
    assert policy["progress_updates_enabled"] is True
    assert policy["show_partial_results_when_useful"] is True
    assert policy["show_failures_and_repairs"] is True
    assert policy["do_not_expose_secrets"] is True
    assert policy["do_not_expose_private_chain_of_thought"] is True
    assert policy["final_response_contains_outcome_and_evidence"] is True


def test_ameer_can_recover_and_resume_without_one_provider_or_operator():
    policy = resilience_policy()
    assert policy["self_operation_required"] is True
    assert policy["self_diagnosis_required"] is True
    assert policy["self_repair_required"] is True
    assert policy["cold_start_recovery_required"] is True
    assert policy["provider_independence"] is True
    assert policy["model_independence"] is True
    assert policy["single_operator_dependency"] is False
    assert policy["resume_persistent_goals_after_recovery"] is True
    assert "software_engineering" in policy["core_domains"]
    assert "financial_analysis_and_operations" in policy["core_domains"]
