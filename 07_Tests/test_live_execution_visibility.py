from pathlib import Path

from kernel.live_execution import LiveExecutionStore


ROOT = Path(__file__).resolve().parents[1]


def test_live_execution_store_updates_one_stage_without_saving_prompt(tmp_path, monkeypatch):
    monkeypatch.delenv("AMEER_DATA_DIR", raising=False)
    store = LiveExecutionStore(tmp_path)
    execution_id = "exec_1234567890abcdef"

    store.begin(execution_id, request_id="request-1")
    store.stage(execution_id, "context", "مراجعة السياق", status="running")
    store.stage(
        execution_id,
        "context",
        "تمت مراجعة السياق",
        status="completed",
        detail="تم تحديد المشروع.",
        evidence={"worker_id": "school", "secret": "must-not-leak"},
    )
    public = store.public(execution_id)

    assert public["status"] == "running"
    assert len(public["stages"]) == 1
    assert public["stages"][0]["status"] == "completed"
    assert public["stages"][0]["evidence"] == {"worker_id": "school"}
    persisted = store.path.read_text(encoding="utf-8")
    assert "must-not-leak" not in persisted
    assert "prompt" not in persisted.lower()


def test_live_execution_store_finishes_and_rejects_guessable_ids(tmp_path, monkeypatch):
    monkeypatch.delenv("AMEER_DATA_DIR", raising=False)
    store = LiveExecutionStore(tmp_path)
    execution_id = "7f2e1297-35c7-4dc4-b7d5-ccdf37b6712a"

    store.begin(execution_id)
    store.stage(execution_id, "verification", "تم التحقق", evidence={"file_count": 2, "files": ["a.py", "b.js"]})
    finished = store.finish(execution_id)

    assert finished["status"] == "completed"
    assert finished["finished_at"]
    assert store.public("short-id") is None


def test_business_chat_live_module_intercepts_ask_and_polls_safe_timeline():
    module = (ROOT / "09_Assets" / "web" / "modules" / "live-execution.js").read_text(encoding="utf-8")
    delivery = (ROOT / "ameer_delivery_bootstrap.py").read_text(encoding="utf-8")
    proactive = (ROOT / "ameer_proactive_bootstrap.py").read_text(encoding="utf-8")

    for required in (
        "X-Ameer-Execution-ID",
        "/ui/executions/",
        "تنفيذ أمير المرئي",
        "live-execution",
        "setInterval(() => refresh(id), 650)",
    ):
        assert required in module
    assert '@app.get("/ui/executions/{execution_id}")' in delivery
    assert 'src="/modules/live-execution.js"' in proactive


def test_server_reports_operational_stages_without_exposing_reasoning():
    source = (ROOT / "ameer_server.py").read_text(encoding="utf-8")

    for stage in ("received", "context", "routing", "worker", "planning", "execution", "response"):
        assert f'"{stage}"' in source
    assert "LIVE_EXECUTIONS.begin" in source
    assert "internal_reasoning" not in source
