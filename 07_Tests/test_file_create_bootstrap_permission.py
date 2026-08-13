"""
test_file_create_bootstrap_permission.py
=========================================
Regression tests for the permanent file.create bootstrap check added to
ExecutiveKernel.__init__.

Context
-------
Production volumes may start without an independent file.create permission
card because preDeployCommand does not persist to the runtime container's
volume. ExecutionAuthorization.check() looks up the permission card by
tool_name ("file.create") first before falling back to the file_operations
capability card, so a missing file.create card causes every file.create
request to be denied even when file_operations is otherwise granted.

ExecutiveKernel._enable_file_create_permission() is a permanent bootstrap
check (analogous to _enable_file_read_permission /
_enable_shell_run_permission) that guarantees the file.create permission
card always exists in a granted state after startup, independent of any
external setup step (pre-deploy commands, volume seeding, etc).

Tests
-----
1. Startup with NO file.create card → card created with status=granted.
2. Startup WITH a correct, already-granted card → no duplicate/mutation.
3. file.read permission is unaffected by the file.create bootstrap.
4. shell.run permission is unaffected by the file.create bootstrap.
5. ExecutionAuthorization.check(file_operations/write/file.create/path in
   runtime_workspace) → approved.
6. build_homepage (P1.5 E2E flow) can access FileExecutor end-to-end.
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
    """Minimal folder structure required for ExecutiveKernel to boot."""
    Path(tmp, ".ameer").mkdir(parents=True, exist_ok=True)
    Path(tmp, "04_Memory").mkdir(parents=True, exist_ok=True)
    Path(tmp, "09_Assets", "runtime_workspace").mkdir(parents=True, exist_ok=True)


def _make_kernel(tmp: str, module_name: str):
    _make_workspace(tmp)
    kernel_mod = _load(
        module_name,
        os.path.join(CODE_ROOT, "kernel", "executive_kernel.py"),
    )
    return kernel_mod.ExecutiveKernel(workspace_root=tmp)


class Test1_NoFileCreateCardOnStartup(unittest.TestCase):
    """1. Startup with NO file.create card → card created with status=granted."""

    def test_card_created_and_granted(self):
        with tempfile.TemporaryDirectory() as tmp:
            kernel = _make_kernel(tmp, "executive_kernel_boot_1")
            card = kernel.permissions.get_for_capability("file.create")
            self.assertIsNotNone(card, "file.create permission card must exist after startup")
            self.assertEqual(card.get("permission_status"), "granted")
            self.assertTrue(card.get("enabled", False))
            self.assertEqual(card.get("granted_by"), "system:file.create_activation")

    def test_scope_matches_expected_policy(self):
        from kernel.execution_authorization import file_create_permission_scope

        with tempfile.TemporaryDirectory() as tmp:
            kernel = _make_kernel(tmp, "executive_kernel_boot_1b")
            card = kernel.permissions.get_for_capability("file.create")
            self.assertEqual(card.get("scope"), file_create_permission_scope())


class Test2_ExistingCorrectCardNotDuplicated(unittest.TestCase):
    """2. Startup WITH correct card already granted → no duplicate created."""

    def test_no_duplicate_card_created(self):
        with tempfile.TemporaryDirectory() as tmp:
            kernel = _make_kernel(tmp, "executive_kernel_boot_2")
            all_perms_after_first_boot = [
                p for p in kernel.permissions.list_all() if p.get("capability_id") == "file.create"
            ]
            self.assertEqual(len(all_perms_after_first_boot), 1)

            # Re-run the bootstrap check again (simulating a second startup)
            kernel._enable_file_create_permission()
            all_perms_after_second_boot = [
                p for p in kernel.permissions.list_all() if p.get("capability_id") == "file.create"
            ]
            self.assertEqual(len(all_perms_after_second_boot), 1)

    def test_granted_at_not_refreshed_when_already_correct(self):
        with tempfile.TemporaryDirectory() as tmp:
            kernel = _make_kernel(tmp, "executive_kernel_boot_2b")
            card_before = kernel.permissions.get_for_capability("file.create")
            granted_at_before = card_before.get("granted_at")

            kernel._enable_file_create_permission()
            card_after = kernel.permissions.get_for_capability("file.create")
            self.assertEqual(card_after.get("granted_at"), granted_at_before)


class Test3_FileReadPermissionUnaffected(unittest.TestCase):
    """3. file.read permission unchanged after bootstrap."""

    def test_file_read_permission_still_granted(self):
        from kernel.execution_authorization import file_read_permission_scope

        with tempfile.TemporaryDirectory() as tmp:
            kernel = _make_kernel(tmp, "executive_kernel_boot_3")
            file_cap = kernel.capabilities.get_by_name("file_operations")
            card = kernel.permissions.get_for_capability(file_cap["capability_id"])
            self.assertIsNotNone(card)
            self.assertEqual(card.get("permission_status"), "granted")
            self.assertEqual(card.get("scope"), file_read_permission_scope())
            self.assertEqual(card.get("granted_by"), "system:file.read_activation")


class Test4_ShellRunPermissionUnaffected(unittest.TestCase):
    """4. shell.run permission unchanged after bootstrap."""

    def test_shell_run_permission_still_granted(self):
        with tempfile.TemporaryDirectory() as tmp:
            kernel = _make_kernel(tmp, "executive_kernel_boot_4")
            shell_cap = kernel.capabilities.get_by_name("shell_execution")
            card = kernel.permissions.get_for_capability(shell_cap["capability_id"])
            self.assertIsNotNone(card)
            self.assertEqual(card.get("permission_status"), "granted")
            self.assertEqual(card.get("granted_by"), "system:shell.run_activation")


class Test5_ExecutionAuthorizationApprovesFileCreate(unittest.TestCase):
    """5. ExecutionAuthorization.check(file_operations/write/file.create/... ) → approved."""

    def test_file_create_check_approved_in_runtime_workspace(self):
        with tempfile.TemporaryDirectory() as tmp:
            kernel = _make_kernel(tmp, "executive_kernel_boot_5")
            result = kernel.execution_auth.check(
                capability_name="file_operations",
                action="write",
                context={
                    "tool_name": "file.create",
                    "target": "09_Assets/runtime_workspace/out.txt",
                },
            )
            self.assertEqual(result["status"], "approved", result)


class Test6_BuildHomepageFileExecutorAccess(unittest.TestCase):
    """6. build_homepage can access FileExecutor end-to-end (P1.5 style flow)."""

    def test_end_to_end_file_creation_via_kernel(self):
        with tempfile.TemporaryDirectory() as tmp:
            kernel = _make_kernel(tmp, "executive_kernel_boot_6")
            tasks = [
                {
                    "id": "home-index",
                    "action": "write",
                    "executor": "file",
                    "target": "09_Assets/runtime_workspace/home/index.html",
                    "content": "<html><body>home</body></html>",
                }
            ]
            report = kernel.execute_task(tasks)
            self.assertTrue(report["accepted"], report)
            self.assertEqual(report["execution"]["completed"], 1)
            self.assertEqual(report["execution"]["failed"], 0)
            self.assertEqual(report["execution"]["blocked"], 0)

            path = Path(tmp, "09_Assets", "runtime_workspace", "home", "index.html")
            self.assertTrue(path.exists())
            self.assertIn("home", path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
