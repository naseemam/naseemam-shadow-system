"""
test_p14_scheduler.py
=====================
P1.4 Scheduler + P1.5 File Executor tests.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CODE_ROOT = os.path.join(ROOT, "06_Code")

if CODE_ROOT not in sys.path:
    sys.path.insert(0, CODE_ROOT)


def _load(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _make_workspace(tmp: str) -> None:
    Path(tmp, ".ameer").mkdir(parents=True, exist_ok=True)
    Path(tmp, "04_Memory").mkdir(parents=True, exist_ok=True)
    Path(tmp, "09_Assets", "runtime_workspace").mkdir(parents=True, exist_ok=True)


def _task(task_id: str, target: str, **extra):
    data = {
        "id": task_id,
        "action": "write",
        "executor": "file",
        "target": target,
        "content": f"content for {task_id}",
    }
    data.update(extra)
    return data


class SchedulerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        _make_workspace(self.tmp)
        mod = _load("scheduler", os.path.join(CODE_ROOT, "kernel", "scheduler.py"))
        self.scheduler = mod.Scheduler(self.tmp)

    def test_scheduler_builds_dependency_batches_for_page_files_then_test(self):
        tasks = [
            _task("index", "09_Assets/runtime_workspace/index.html", priority="high"),
            _task("style", "09_Assets/runtime_workspace/style.css", depends_on=["index"], parallel_safe=True, priority="medium"),
            _task("script", "09_Assets/runtime_workspace/script.js", depends_on=["index"], parallel_safe=True, priority="medium"),
            _task("test", "09_Assets/runtime_workspace/report.txt", depends_on=["index", "style", "script"], priority="low"),
        ]

        result = self.scheduler.schedule(tasks)

        self.assertTrue(result["accepted"])
        self.assertEqual(result["execution_order"], ["index", "style", "script", "test"])
        self.assertEqual(result["batches"][0]["task_ids"], ["index"])
        self.assertEqual(result["batches"][1]["task_ids"], ["style", "script"])
        self.assertTrue(result["batches"][1]["parallel"])
        self.assertEqual(result["batches"][2]["task_ids"], ["test"])

    def test_scheduler_applies_priority_inside_ready_set(self):
        tasks = [
            _task("low", "09_Assets/runtime_workspace/low.txt", priority="low"),
            _task("high", "09_Assets/runtime_workspace/high.txt", priority="high"),
            _task("medium", "09_Assets/runtime_workspace/medium.txt", priority="medium"),
        ]

        result = self.scheduler.schedule(tasks)

        self.assertEqual(result["execution_order"], ["high", "medium", "low"])

    def test_scheduler_blocks_dependents_of_blocked_tasks(self):
        tasks = [
            _task("a", "09_Assets/runtime_workspace/a.txt", status="blocked"),
            _task("b", "09_Assets/runtime_workspace/b.txt", depends_on=["a"]),
            _task("c", "09_Assets/runtime_workspace/c.txt"),
        ]

        result = self.scheduler.schedule(tasks)

        self.assertTrue(result["accepted"])
        self.assertEqual(result["execution_order"], ["c"])
        blocked = {item["id"]: item for item in result["blocked"]}
        self.assertEqual(blocked["a"]["reason"], "task_blocked")
        self.assertEqual(blocked["b"]["reason"], "blocked_dependencies")
        self.assertEqual(blocked["b"]["blocked_by"], ["a"])

    def test_scheduler_rejects_cycles_defensively(self):
        tasks = [
            _task("a", "09_Assets/runtime_workspace/a.txt", depends_on=["b"]),
            _task("b", "09_Assets/runtime_workspace/b.txt", depends_on=["a"]),
        ]

        result = self.scheduler.schedule(tasks)

        self.assertFalse(result["accepted"])
        self.assertTrue(any(item["reason"] == "dependency_cycle" for item in result["blocked"]))


class KernelExecutionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        _make_workspace(self.tmp)
        kernel_mod = _load("executive_kernel_p14", os.path.join(CODE_ROOT, "kernel", "executive_kernel.py"))
        self.kernel = kernel_mod.ExecutiveKernel(workspace_root=self.tmp)

    def test_execute_task_creates_runtime_workspace_files(self):
        tasks = [
            _task("index", "09_Assets/runtime_workspace/index.html", content="<h1>home</h1>", priority="high"),
            _task("style", "09_Assets/runtime_workspace/style.css", content="body{}", depends_on=["index"], parallel_safe=True),
            _task("script", "09_Assets/runtime_workspace/script.js", content="console.log('ok')", depends_on=["index"], parallel_safe=True),
        ]

        result = self.kernel.execute_task(tasks)

        self.assertTrue(result["accepted"])
        self.assertEqual(result["execution"]["completed"], 3)
        self.assertEqual(result["execution"]["failed"], 0)
        for relative_path in [
            "09_Assets/runtime_workspace/index.html",
            "09_Assets/runtime_workspace/style.css",
            "09_Assets/runtime_workspace/script.js",
        ]:
            self.assertTrue(Path(self.tmp, relative_path).exists(), f"Missing {relative_path}")

    def test_execute_task_returns_schedule_and_execution_payloads(self):
        result = self.kernel.execute_task([
            _task("index", "09_Assets/runtime_workspace/index.html", content="<main></main>")
        ])

        self.assertIn("schedule", result)
        self.assertIn("execution", result)
        self.assertEqual(result["schedule"]["execution_order"], ["index"])
        self.assertEqual(result["execution"]["results"][0]["status"], "completed")


if __name__ == "__main__":
    unittest.main()
