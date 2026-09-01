from kernel.ameer_harness_identity import harness_identity_policy
from kernel.capability_skill_registry import skill_registry_policy
from kernel.hilm_data_source import data_source_policy
from kernel.hilm_management_intelligence import management_intelligence_policy
from kernel.incident_recovery_loop import recovery_decision
from kernel.persistent_goal_engine import proactive_task_policy


def test_ameer_identity_is_not_owned_by_model_provider():
    p = harness_identity_policy()
    assert p["ameer_is_not_model_provider"] is True
    assert p["memory_owner"] == "ameer_platform"
    assert p["model_role"] == "replaceable_inference_engine"
    assert p["provider_change_must_not_migrate_identity"] is True


def test_hilm_uses_single_source_of_truth():
    p = data_source_policy()
    assert p["mode"] == "single_source_of_truth"
    assert p["all_systems_share_same_state"] is True
    for entity in ("services", "service_prices", "bookings", "customers", "employees", "inventory_items", "sales"):
        assert entity in p["entities"]


def test_workers_use_skills_without_raw_service_credentials():
    p = skill_registry_policy()
    assert p["workers_use_capability_handles"] is True
    assert p["workers_do_not_need_raw_service_keys"] is True
    assert "create_booking" in p["skills"]
    assert "issue_invoice" in p["skills"]


def test_routine_incident_fix_does_not_require_approval():
    d = recovery_decision("restart_existing_service", {"existing_asset": True})
    assert d["founder_approval_required"] is False
    assert d["may_execute_fix_now"] is True
    assert d["failure_is_not_an_approval_gate"] is True


def test_persistent_goal_survives_turns_and_generates_next_tasks():
    p = proactive_task_policy()
    assert p["persistent_goal_survives_chat_turns"] is True
    assert p["proactive_task_generator_enabled"] is True
    assert p["routine_execution_does_not_require_restatement_each_day"] is True


def test_hilm_intelligence_covers_pos_invoicing_and_ready_actions():
    p = management_intelligence_policy()
    assert "pos_cashier" in p["management_modules"]
    assert "invoicing" in p["management_modules"]
    assert "implement_pos" in p["system_build_capabilities"]
    assert p["analytics"]["calculate_offer_margin"] is True
    assert p["analytics"]["prepare_ready_action"] is True
