import json
from pathlib import Path

from kernel.cost_ledger import CostLedger
from kernel.worker_runtime import WorkerRuntimeRegistry


def test_cost_ledger_records_usage_without_secrets(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "AMEER_MODEL_PRICING_JSON",
        json.dumps({"gpt-test": {"input_per_1m": 1.0, "output_per_1m": 2.0}}),
    )
    ledger = CostLedger(tmp_path)
    event = ledger.record(
        task_id="task-1",
        run_id="run-1",
        agent_id="engineering",
        provider="test-provider",
        model="gpt-test",
        usage={"prompt_tokens": 1000, "completion_tokens": 500, "total_tokens": 1500},
        status="completed",
        latency_ms=12.5,
    )
    assert event["total_tokens"] == 1500
    assert event["estimated_cost_usd"] == 0.002
    assert ledger.summary()["by_agent"][0]["agent_id"] == "engineering"
    assert "prompt" not in json.dumps(ledger.snapshot())
    assert "api_key" not in json.dumps(ledger.snapshot())


def test_worker_dispatch_persists_cost_event(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "AMEER_MODEL_PRICING_JSON",
        json.dumps({"gpt-test": {"input_per_1m": 1.0, "output_per_1m": 2.0}}),
    )
    runtime = WorkerRuntimeRegistry(tmp_path)
    runtime.register_runtime("engineering", provider="test-provider", model="gpt-test", adapter="test", status="ready")
    runtime.register_handler(
        "engineering",
        lambda objective, context: {
            "status": "completed",
            "model": "gpt-test",
            "content": "ok",
            "usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
        },
    )
    result = runtime.dispatch("engineering", "safe test", {"task_id": "task-2"})
    assert result["status"] == "completed"
    assert result["result"]["cost"]["total_tokens"] == 150
    events = runtime.cost_ledger.list(task_id="task-2")
    assert len(events) == 1
    assert events[0]["run_id"] == result["run_id"]
    assert events[0]["estimated_cost_usd"] == 0.0002
