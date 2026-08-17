from pathlib import Path

from kernel.worker_runtime import WorkerRuntimeRegistry


def test_defaults_are_registered_but_not_claimed_ready(tmp_path: Path):
    registry = WorkerRuntimeRegistry(tmp_path)
    snapshot = registry.snapshot()
    assert snapshot["total_count"] == 7
    assert snapshot["ready_count"] == 0
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
