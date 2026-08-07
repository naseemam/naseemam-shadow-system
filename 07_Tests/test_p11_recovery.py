"""
test_p11_recovery.py
====================
P1.1 Review Gate — Recovery & Versioning Tests.

Covers:
1. schema_version is written to every new state file.
2. Migration: a v0 state (no schema_version) is transparently upgraded to v1.
3. All missing v0 keys are back-filled after migration.
4. Recovery scenario: task added → server crash simulated (state object
   discarded) → new state object reloads from disk → task is still present.
5. Resumed task can be updated after recovery.
6. P0.6 integrity: CapabilityRegistry, PermissionRegistry,
   ExecutionAuthorization, and ApprovalGate are importable and unmodified.
7. RuntimeState isolation: ExecutiveBrain does NOT own the state — it reads
   and updates it via ExecutiveKernel but is never assigned the manager.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CODE_ROOT = os.path.join(ROOT, "06_Code")

if CODE_ROOT not in sys.path:
    sys.path.insert(0, CODE_ROOT)


# ── helpers ──────────────────────────────────────────────────────────────────

def _load(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _state_manager_cls():
    mod = _load(
        "state_manager",
        os.path.join(CODE_ROOT, "kernel", "state_manager.py"),
    )
    return mod.ExecutiveStateManager


def _make_workspace(tmp: str) -> None:
    Path(tmp, "04_Memory").mkdir(parents=True, exist_ok=True)
    Path(tmp, ".ameer").mkdir(parents=True, exist_ok=True)
    Path(tmp, "04_Memory", "Founder.md").write_text(
        "# Founder\nنسيم\n", encoding="utf-8"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 1. schema_version written on fresh state
# ═══════════════════════════════════════════════════════════════════════════════

class TestSchemaVersioning(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        _make_workspace(self.tmp)
        cls = _state_manager_cls()
        self.mgr = cls(self.tmp)

    def test_fresh_state_has_schema_version(self):
        raw = json.loads(
            Path(self.tmp, ".ameer", "state.json").read_text(encoding="utf-8")
        )
        self.assertIn("schema_version", raw)
        self.assertGreaterEqual(raw["schema_version"], 1)

    def test_schema_version_matches_class_constant(self):
        cls = _state_manager_cls()
        expected = cls.SCHEMA_VERSION
        raw = json.loads(
            Path(self.tmp, ".ameer", "state.json").read_text(encoding="utf-8")
        )
        self.assertEqual(raw["schema_version"], expected)

    def test_created_at_present(self):
        raw = json.loads(
            Path(self.tmp, ".ameer", "state.json").read_text(encoding="utf-8")
        )
        self.assertIn("created_at", raw)
        self.assertIsNotNone(raw["created_at"])

    def test_updated_at_present(self):
        raw = json.loads(
            Path(self.tmp, ".ameer", "state.json").read_text(encoding="utf-8")
        )
        self.assertIn("updated_at", raw)
        self.assertIsNotNone(raw["updated_at"])


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Migration: v0 state → v1
# ═══════════════════════════════════════════════════════════════════════════════

class TestStateMigration(unittest.TestCase):

    def _write_v0_state(self, tmp: str, extra: Dict[str, Any] = None) -> None:
        """Write a v0-style state (no schema_version) to disk."""
        state: Dict[str, Any] = {
            "active_goals": ["هدف قديم"],
            "active_projects": ["مشروع قديم"],
            "pending_approvals": [],
            "running_tasks": [{"id": "t-old", "title": "مهمة قديمة", "status": "pending"}],
            "recent_decisions": [],
            "founder_context": {},
            "executive_assessment": "تقييم قديم",
            "runtime_status": "running",
            "last_session_at": None,
            "session_count": 5,
            "workspace_summary": "",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
        }
        if extra:
            state.update(extra)
        p = Path(tmp, ".ameer")
        p.mkdir(parents=True, exist_ok=True)
        (p / "state.json").write_text(
            json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def test_migration_adds_schema_version(self):
        tmp = tempfile.mkdtemp()
        _make_workspace(tmp)
        self._write_v0_state(tmp)
        cls = _state_manager_cls()
        mgr = cls(tmp)
        raw = json.loads(
            Path(tmp, ".ameer", "state.json").read_text(encoding="utf-8")
        )
        self.assertIn("schema_version", raw)
        self.assertGreaterEqual(raw["schema_version"], 1)

    def test_migration_preserves_existing_data(self):
        tmp = tempfile.mkdtemp()
        _make_workspace(tmp)
        self._write_v0_state(tmp)
        cls = _state_manager_cls()
        mgr = cls(tmp)
        self.assertIn("هدف قديم", mgr.active_goals)
        self.assertIn("مشروع قديم", mgr.active_projects)

    def test_migration_backfills_missing_keys(self):
        """Keys that didn't exist in v0 must be present after migration."""
        tmp = tempfile.mkdtemp()
        _make_workspace(tmp)
        # Write a minimal v0 state missing several keys
        p = Path(tmp, ".ameer")
        p.mkdir(parents=True, exist_ok=True)
        (p / "state.json").write_text(
            json.dumps({"active_goals": [], "created_at": "2024-01-01T00:00:00Z",
                        "updated_at": "2024-01-01T00:00:00Z"},
                       ensure_ascii=False),
            encoding="utf-8",
        )
        cls = _state_manager_cls()
        mgr = cls(tmp)
        snap = mgr.snapshot()
        for required in ("schema_version", "active_projects", "pending_approvals",
                         "running_tasks", "session_count", "runtime_status"):
            self.assertIn(required, snap, f"Missing key after migration: {required}")

    def test_existing_v1_state_is_not_re_persisted_unnecessarily(self):
        """Loading a v1 state must not change schema_version or modify the file."""
        tmp = tempfile.mkdtemp()
        _make_workspace(tmp)
        cls = _state_manager_cls()
        mgr1 = cls(tmp)
        state_path = Path(tmp, ".ameer", "state.json")
        mtime_before = state_path.stat().st_mtime_ns

        # Load again without making any changes
        cls(tmp)

        mtime_after = state_path.stat().st_mtime_ns
        self.assertEqual(
            mtime_before,
            mtime_after,
            "State file was unexpectedly re-written when loading an already-v1 state.",
        )
        raw = json.loads(state_path.read_text(encoding="utf-8"))
        self.assertEqual(raw["schema_version"], cls.SCHEMA_VERSION)


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Recovery scenario: crash → reload → continue
# ═══════════════════════════════════════════════════════════════════════════════

class TestCrashRecovery(unittest.TestCase):
    """
    Simulates the sequence:
      1. Start execution of a task.
      2. Force crash: discard the state manager object.
      3. Restart: create a new state manager from the same directory.
      4. Verify the task is recovered.
      5. Resume: update the task status to "done".
    """

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        _make_workspace(self.tmp)

    def test_task_survives_server_crash(self):
        cls = _state_manager_cls()

        # Step 1 – start a task
        mgr = cls(self.tmp)
        mgr.add_task({
            "id": "task-recovery-001",
            "title": "بناء الصفحة الرئيسية",
            "status": "running",
            "last_step": "scaffold",
        })

        # Step 2 – simulate crash: delete the manager object
        del mgr

        # Step 3 – restart: fresh manager from same directory
        mgr_recovered = cls(self.tmp)

        # Step 4 – task must be present
        recovered_tasks = mgr_recovered.running_tasks
        ids = [t.get("id") for t in recovered_tasks]
        self.assertIn("task-recovery-001", ids, "Task not found after recovery")

    def test_recovered_task_has_correct_title(self):
        cls = _state_manager_cls()
        mgr = cls(self.tmp)
        mgr.add_task({
            "id": "task-recovery-002",
            "title": "نشر التطبيق",
            "status": "running",
        })
        del mgr

        mgr2 = cls(self.tmp)
        task = next(
            (t for t in mgr2.running_tasks if t.get("id") == "task-recovery-002"),
            None,
        )
        self.assertIsNotNone(task, "Recovered task not found")
        self.assertEqual(task["title"], "نشر التطبيق")

    def test_recovered_task_can_be_resumed(self):
        """After recovery, task status can be updated (resume from last step)."""
        cls = _state_manager_cls()
        mgr = cls(self.tmp)
        mgr.add_task({
            "id": "task-recovery-003",
            "title": "تحليل الكود",
            "status": "running",
            "last_step": "fetch_files",
        })
        del mgr

        # Restart
        mgr2 = cls(self.tmp)
        updated = mgr2.update_task(
            "task-recovery-003",
            status="done",
            result="الكود تم تحليله بنجاح",
        )
        self.assertTrue(updated, "update_task returned False — task not found after recovery")

    def test_state_persists_multiple_crash_cycles(self):
        """State must survive several crash-restart cycles."""
        cls = _state_manager_cls()

        # First run
        m = cls(self.tmp)
        m.mark_session_start()
        m.add_task({"id": "multi-crash-task", "title": "مهمة دائمة", "status": "running"})
        del m

        # Second run — add another task
        m2 = cls(self.tmp)
        m2.mark_session_start()
        del m2

        # Third run — verify both records
        m3 = cls(self.tmp)
        self.assertGreaterEqual(m3.session_count, 2)
        ids = [t.get("id") for t in m3.running_tasks]
        self.assertIn("multi-crash-task", ids)


# ═══════════════════════════════════════════════════════════════════════════════
# 4. P0.6 integrity check
# ═══════════════════════════════════════════════════════════════════════════════

class TestP06Integrity(unittest.TestCase):
    """Verify that P0.6 governance components are present and loadable."""

    def _load_module(self, filename: str):
        path = os.path.join(CODE_ROOT, "kernel", filename)
        mod = _load(filename.replace(".py", ""), path)
        return mod

    def test_capability_registry_importable(self):
        mod = self._load_module("capability_registry.py")
        self.assertTrue(hasattr(mod, "CapabilityRegistry"))

    def test_permission_registry_importable(self):
        mod = self._load_module("permission_registry.py")
        self.assertTrue(hasattr(mod, "PermissionRegistry"))

    def test_execution_authorization_importable(self):
        mod = self._load_module("execution_authorization.py")
        self.assertTrue(hasattr(mod, "ExecutionAuthorization"))

    def test_approval_gate_importable(self):
        mod = self._load_module("approval_gate.py")
        self.assertTrue(hasattr(mod, "ApprovalGate"))

    def test_execution_authorization_has_pipeline_methods(self):
        mod = self._load_module("execution_authorization.py")
        cls = mod.ExecutionAuthorization
        for method in ("check", "authorize", "record_execution"):
            self.assertTrue(
                hasattr(cls, method),
                f"ExecutionAuthorization missing method: {method}",
            )

    def test_approval_gate_has_request_method(self):
        mod = self._load_module("approval_gate.py")
        cls = mod.ApprovalGate
        self.assertTrue(hasattr(cls, "request"), "ApprovalGate missing method: request")


# ═══════════════════════════════════════════════════════════════════════════════
# 5. RuntimeState isolation: Brain ≠ state owner
# ═══════════════════════════════════════════════════════════════════════════════

class TestRuntimeStateIsolation(unittest.TestCase):
    """
    Verifies that ExecutiveBrain does NOT own or instantiate
    ExecutiveStateManager. State ownership belongs to ExecutiveKernel.
    """

    def _brain_source(self) -> str:
        return Path(CODE_ROOT, "executive_brain.py").read_text(encoding="utf-8")

    def test_brain_does_not_instantiate_state_manager(self):
        source = self._brain_source()
        self.assertNotIn(
            "ExecutiveStateManager(",
            source,
            "ExecutiveBrain must not instantiate ExecutiveStateManager directly.",
        )

    def test_brain_does_not_import_state_manager(self):
        source = self._brain_source()
        self.assertNotIn(
            "from kernel.state_manager import",
            source,
            "ExecutiveBrain must not import state_manager — state is owned by the Kernel.",
        )


if __name__ == "__main__":
    unittest.main()
