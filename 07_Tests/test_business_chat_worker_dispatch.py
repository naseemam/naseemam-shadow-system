import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "06_Code"))

from kernel.task_decomposer import TaskDecomposer
from kernel.worker_runtime import WorkerRuntimeRegistry


def test_worker_request_is_not_misclassified_as_pending_task_replay(tmp_path: Path):
    decomposer = TaskDecomposer(str(tmp_path))
    result = decomposer.decompose("اختبر عامل التصميم ونفذ فحصًا لقدرته على تصميم واجهة بسيطة")
    assert result["intent"] != "execute_pending_tasks"


def test_explicit_pending_queue_command_remains_supported(tmp_path: Path):
    decomposer = TaskDecomposer(str(tmp_path))
    result = decomposer.decompose("نفذ المهام المعلقة")
    assert result["intent"] == "execute_pending_tasks"


def test_business_chat_worker_marker_resolves_design_worker():
    import ameer_server

    assert ameer_server._requested_worker_id("استدع عامل التصميم ونفذ فحصًا") == "design"
    assert ameer_server._requested_worker_id("صمم واجهة جميلة") == ""


def test_business_chat_auto_routes_specialist_analysis():
    import ameer_server

    assert ameer_server._select_worker_id("حلل واجهة محادثة الأعمال") == ("design", "automatic")
    assert ameer_server._select_worker_id("راجع بيانات المخزون والحجوزات") == ("store", "automatic")
    assert ameer_server._select_worker_id("ابحث عن مقارنة بين حلول الواجهة") == ("research", "automatic")
    assert ameer_server._select_worker_id("حلل متطلبات امتثال تخصصية للمشروع") == ("specialist", "automatic")


def test_business_chat_auto_routing_does_not_replace_kernel_execution():
    import ameer_server

    assert ameer_server._select_worker_id("أنشئ موقعًا لحلم الندى") == ("", "")
    assert ameer_server._select_worker_id("اختبر كود الواجهة") == ("", "")


def test_worker_runtime_dispatch_creates_traceable_run(tmp_path: Path):
    runtime = WorkerRuntimeRegistry(tmp_path)
    runtime.register_runtime("design", provider="test", model="test-model", adapter="test-adapter", status="ready")
    runtime.register_handler(
        "design",
        lambda objective, context: {"status": "completed", "content": f"done:{objective}", "usage": {}},
    )

    result = runtime.dispatch("design", "اختبر التصميم", {"mode": "business_chat_worker_dispatch"})
    assert result["status"] == "completed"
    assert result["worker_id"] == "design"
    assert result["run_id"]
    assert result["result"]["content"] == "done:اختبر التصميم"


def test_dispatcher_reports_executor_error_distinctly(tmp_path: Path):
    from types import SimpleNamespace
    from kernel.tool_dispatcher import ToolDispatcher
    from kernel.tool_registry import ToolRegistry

    class AllowBoundary:
        def evaluate(self, **kwargs):
            return SimpleNamespace(verdict="ALLOW", reason="allowed", detail={})

    class ApprovedAuth:
        def check(self, **kwargs):
            return {"status": "approved", "request_id": "test-executor-error"}

    def failing_executor(_payload):
        raise OSError("file name too long")

    dispatcher = ToolDispatcher(
        tool_registry=ToolRegistry(),
        execution_boundary=AllowBoundary(),
        execution_authorization=ApprovedAuth(),
        executor=failing_executor,
        workspace_root=tmp_path,
    )
    result = dispatcher.dispatch(
        tool_name="file.create",
        context={"target": "09_Assets/runtime_workspace/a.txt", "content": "x"},
        guardian={"status": "pass"},
        intent="build_homepage",
    )
    assert result["decision"] == "DENY"
    assert result["reason"] == "executor_execution_failed"
    assert result["detail"]["error"] == "file name too long"
