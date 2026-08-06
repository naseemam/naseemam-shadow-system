import importlib.util
import json
import os
import sys
import tempfile
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MODULE_PATH = os.path.join(ROOT, "06_Code", "runtime_state.py")

spec = importlib.util.spec_from_file_location("runtime_state", MODULE_PATH)
runtime_state = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = runtime_state
assert spec.loader is not None
spec.loader.exec_module(runtime_state)

RuntimeStateStore = runtime_state.RuntimeStateStore


class RuntimeStateTests(unittest.TestCase):
    def test_initial_state_contains_required_fields(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = RuntimeStateStore(workspace_root=tmpdir)
            snap = store.snapshot()

            required = {
                "run_id",
                "current_task_id",
                "current_step",
                "running_executors",
                "progress_percent",
                "eta_seconds",
                "paused",
                "cancelled",
                "completed",
                "last_update_at",
            }
            self.assertTrue(required.issubset(set(snap.keys())))

    def test_state_persists_between_instances(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = RuntimeStateStore(workspace_root=tmpdir)
            store.begin_run("run-001", initial_step="plan")
            store.set_running_executors(["file", "terminal"])
            store.set_progress(35)
            store.set_eta(120)
            store.add_active_task("task-1", executor="file")

            reloaded = RuntimeStateStore(workspace_root=tmpdir)
            snap = reloaded.snapshot()

            self.assertEqual(snap["run_id"], "run-001")
            self.assertEqual(snap["current_step"], "plan")
            self.assertEqual(snap["running_executors"], ["file", "terminal"])
            self.assertEqual(snap["progress_percent"], 35)
            self.assertEqual(snap["eta_seconds"], 120)
            self.assertEqual(len(snap["active_tasks"]), 1)
            self.assertEqual(snap["active_tasks"][0]["task_id"], "task-1")

    def test_restart_keeps_active_task_list(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = RuntimeStateStore(workspace_root=tmpdir)
            store.begin_run("run-restore", initial_step="execute")
            store.add_active_task("task-a", executor="file")
            store.add_active_task("task-b", executor="terminal")

            restarted = RuntimeStateStore(workspace_root=tmpdir)
            snap = restarted.snapshot()

            ids = [item["task_id"] for item in snap["active_tasks"]]
            self.assertEqual(ids, ["task-a", "task-b"])

    def test_complete_task_moves_from_active_to_completed(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = RuntimeStateStore(workspace_root=tmpdir)
            store.begin_run("run-002", initial_step="execute")
            store.add_active_task("task-9", executor="file")
            snap = store.complete_task("task-9", status="succeeded")

            self.assertEqual(snap["active_tasks"], [])
            self.assertEqual(len(snap["completed_tasks"]), 1)
            self.assertEqual(snap["completed_tasks"][0]["task_id"], "task-9")
            self.assertEqual(snap["completed_tasks"][0]["status"], "succeeded")

    def test_complete_marks_run_finished(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = RuntimeStateStore(workspace_root=tmpdir)
            store.begin_run("run-done", initial_step="reflect")
            snap = store.complete()

            self.assertTrue(snap["completed"])
            self.assertFalse(snap["cancelled"])
            self.assertEqual(snap["progress_percent"], 100)

    def test_runtime_state_file_is_json_on_disk(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = RuntimeStateStore(workspace_root=tmpdir)
            store.begin_run("run-json", initial_step="parse")

            state_path = os.path.join(tmpdir, ".ameer", "runtime_state.json")
            self.assertTrue(os.path.exists(state_path))
            with open(state_path, "r", encoding="utf-8") as handle:
                payload = json.loads(handle.read())
            self.assertEqual(payload.get("run_id"), "run-json")


if __name__ == "__main__":
    unittest.main()
