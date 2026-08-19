from pathlib import Path

from kernel.worker_runtime import WorkerRuntimeRegistry


def test_defaults_are_registered_but_not_claimed_ready(tmp_path: Path):
    registry = WorkerRuntimeRegistry(tmp_path)
    snapshot = registry.snapshot()
    assert snapshot["total_count"] == 9
    assert snapshot["ready_count"] == 0
    specialist = registry.get("specialist")
    assert specialist["status"] == "unavailable"
    assert specialist["reason"] == "worker_runtime_not_ready"
    design = registry.get("design")
    assert design["status"] == "unavailable"
    assert design["reason"] == "worker_runtime_not_ready"


def test_ready_worker_dispatch_has_a_run_record(tmp_path: Path):
    registry = WorkerRuntimeRegistry(tmp_path)
    registry.register_runtime(
        "design", provider="test", model="design-test", adapter="local", status="ready"
    )
    registry.register_handler("design", lambda objective, context: {
        "status": "completed", "objective": objective, "context": context
    })
    result = registry.dispatch("design", "حلل واجهة المستخدم", {"project": "ameer"})
    assert result["status"] == "completed"
    assert result["run_id"]
    assert result["result"]["objective"] == "حلل واجهة المستخدم"
    assert registry.get("design")["status"] == "ready"


def test_missing_worker_runtime_reports_specific_reason(tmp_path: Path):
    registry = WorkerRuntimeRegistry(tmp_path)
    result = registry.dispatch("engineering", "حسن واجهة المستخدم")
    assert result["status"] == "unavailable"
    assert result["reason"] == "worker_runtime_not_ready"
    assert "human" not in str(result).lower()


def test_on_demand_specialist_dispatch_is_internal_and_traceable(tmp_path: Path):
    registry = WorkerRuntimeRegistry(tmp_path)
    registry.register_runtime(
        "specialist", provider="test", model="specialist-test", adapter="local", status="ready"
    )
    registry.register_handler(
        "specialist",
        lambda objective, context: {"status": "completed", "content": "specialist result", "context": context},
    )

    result = registry.dispatch("specialist", "حلل متطلبات امتثال تخصصية", {"ameer_review": True})

    assert result["status"] == "completed"
    assert result["run_id"]
    policy = result["result"]["context"]["access_policy"]
    assert policy["worker_id"] == "specialist"
    assert policy["external_effect"]["enabled"] is False
    assert policy["external_effect"]["approval"] == "founder_final"
