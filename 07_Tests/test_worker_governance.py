import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CODE_ROOT = ROOT / "06_Code"
for import_root in (ROOT, CODE_ROOT):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))

from kernel.worker_runtime import DEFAULT_WORKERS, WorkerRuntimeRegistry
from ameer_server import _probe_has_non_negated_forbidden_term


def test_probe_guard_ignores_negated_external_terms():
    assert not _probe_has_non_negated_forbidden_term("اذكر مجال مسؤوليتك دون إرسال أو نشر")
    assert not _probe_has_non_negated_forbidden_term("حلل المهمة بدون حذف أو دمج")
    assert not _probe_has_non_negated_forbidden_term("لا تنشر أي شيء")


def test_probe_guard_blocks_real_external_terms():
    assert _probe_has_non_negated_forbidden_term("انشر الموقع في الإنتاج")
    assert _probe_has_non_negated_forbidden_term("send the email")
    assert _probe_has_non_negated_forbidden_term("احذف السجل")


def test_all_workers_receive_governed_internal_access_policy(tmp_path: Path):
    registry = WorkerRuntimeRegistry(tmp_path)
    snapshot = registry.snapshot()
    assert set(DEFAULT_WORKERS) == {item["worker_id"] for item in snapshot["workers"]}
    for worker in snapshot["workers"]:
        policy = worker["access_policy"]
        assert policy["read"]["enabled"] is True
        assert policy["write"]["enabled"] is True
        assert policy["execute_internal"]["enabled"] is True
        assert policy["external_effect"]["enabled"] is False
        assert policy["external_effect"]["approval"] == "founder_final"


def test_dispatch_context_identifies_ameer_and_policy(tmp_path: Path):
    registry = WorkerRuntimeRegistry(tmp_path)
    registry.register_runtime("engineering", provider="test", model="test", adapter="local", status="ready")
    registry.register_handler("engineering", lambda objective, context: {"status": "completed", "context": context})
    result = registry.dispatch("engineering", "حلل الكود", {})
    context = result["result"]["context"]
    assert context["delegated_by"] == "ameer"
    assert context["access_policy"]["write"]["approval"] == "ameer_review"
    assert context["access_policy"]["external_effect"]["enabled"] is False
