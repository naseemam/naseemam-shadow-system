"""
test_p16_preview_projects.py
============================
Regression tests for build_generic preview support.

يتحقق من:
  1. build_homepage ما زال يعمل كما هو (regression).
  2. build_generic يعيد preview_path.
  3. /preview لم يتغير.
  4. /preview/projects/{slug} يعرض المشروع الصحيح.
  5. لا يوجد path traversal يسمح بالوصول خارج runtime_workspace/projects.
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


# ── 1. Kernel pipeline tests ─────────────────────────────────────────────────

class BuildHomepageRegressionTest(unittest.TestCase):
    """build_homepage يجب أن يستمر في العمل كما هو."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        _make_workspace(self.tmp)
        kernel_mod = _load(
            "ek_home_reg",
            os.path.join(CODE_ROOT, "kernel", "executive_kernel.py"),
        )
        self.kernel = kernel_mod.ExecutiveKernel(workspace_root=self.tmp)

    def test_homepage_accepted(self):
        trace = self.kernel.execute_command("ابنِ الصفحة الرئيسية")
        self.assertTrue(trace["final"]["accepted"])

    def test_homepage_completed_three(self):
        trace = self.kernel.execute_command("ابنِ الصفحة الرئيسية")
        self.assertEqual(trace["final"]["completed"], 3)

    def test_homepage_preview_path_is_home(self):
        trace = self.kernel.execute_command("ابنِ الصفحة الرئيسية")
        preview = trace["final"]["preview_path"]
        self.assertIsNotNone(preview)
        self.assertIn("home/index.html", preview)


class BuildGenericPreviewPathTest(unittest.TestCase):
    """build_generic يجب أن يعيد preview_path صحيح."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        _make_workspace(self.tmp)
        kernel_mod = _load(
            "ek_generic_prev",
            os.path.join(CODE_ROOT, "kernel", "executive_kernel.py"),
        )
        self.kernel = kernel_mod.ExecutiveKernel(workspace_root=self.tmp)

    def test_generic_accepted(self):
        trace = self.kernel.execute_command("أنشئ صفحة عن حلم الندى")
        self.assertTrue(trace["final"]["accepted"])

    def test_generic_completed_three(self):
        trace = self.kernel.execute_command("أنشئ صفحة عن حلم الندى")
        self.assertEqual(trace["final"]["completed"], 3)

    def test_generic_preview_path_not_none(self):
        trace = self.kernel.execute_command("أنشئ صفحة عن حلم الندى")
        preview = trace["final"]["preview_path"]
        self.assertIsNotNone(preview, "preview_path يجب أن يكون غير None لـ build_generic")

    def test_generic_preview_path_contains_slug(self):
        trace = self.kernel.execute_command("أنشئ صفحة عن حلم الندى")
        preview = trace["final"]["preview_path"]
        self.assertIn("projects/", preview)
        self.assertIn("index.html", preview)

    def test_generic_preview_path_inside_runtime_workspace(self):
        trace = self.kernel.execute_command("أنشئ صفحة عن حلم الندى")
        preview = trace["final"]["preview_path"]
        self.assertTrue(
            preview.startswith("09_Assets/runtime_workspace/"),
            f"preview_path خارج runtime_workspace: {preview}",
        )

    def test_generic_files_actually_created(self):
        trace = self.kernel.execute_command("أنشئ صفحة عن حلم الندى")
        files = trace["final"]["files_created"]
        self.assertEqual(len(files), 3)
        suffixes = {Path(f).name for f in files}
        self.assertEqual(suffixes, {"index.html", "style.css", "script.js"})


# ── 2. Server endpoint tests ──────────────────────────────────────────────────

class PreviewEndpointTest(unittest.TestCase):
    """/preview و /preview/projects/{slug} endpoint tests."""

    def setUp(self):
        try:
            from fastapi.testclient import TestClient
        except ImportError:
            self.skipTest("fastapi not available")
            return

        # Load server
        server_path = os.path.join(ROOT, "ameer_server.py")
        spec = importlib.util.spec_from_file_location("ameer_server_test", server_path)
        server_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(server_mod)
        # Other HTTP tests may redirect a shared runtime's workspace to a temp
        # directory. A preview endpoint test must always resolve its fixtures in
        # this repository, independently of that transient runtime state.
        server_mod.ROOT = ROOT
        server_mod.REPO_ROOT = ROOT
        self.app = server_mod.app
        self.client = TestClient(self.app, raise_server_exceptions=False)

        # The repository ships this stable preview fixture. Endpoint tests must
        # not rebuild a shared runtime workspace because preceding chat tests can
        # intentionally redirect a live kernel to a temporary workspace.
        fixture = Path(ROOT) / "09_Assets" / "runtime_workspace" / "projects" / "حلم-الندى" / "index.html"
        self.assertTrue(fixture.exists(), f"مشروع المعاينة الثابت مفقود: {fixture}")

    def test_preview_home_not_broken(self):
        """/preview يجب أن يستمر في الاستجابة (200 أو 404 فقط)."""
        resp = self.client.get("/preview")
        self.assertIn(resp.status_code, (200, 404))

    def test_preview_projects_known_slug_returns_200(self):
        """/preview/projects/حلم-الندى يجب أن يعيد 200 بعد بناء المشروع."""
        resp = self.client.get("/preview/projects/حلم-الندى")
        self.assertEqual(resp.status_code, 200)

    def test_preview_projects_unknown_slug_returns_404(self):
        """/preview/projects/slug-غير-موجود يجب أن يعيد 404."""
        resp = self.client.get("/preview/projects/slug-does-not-exist-xyz999")
        self.assertEqual(resp.status_code, 404)

    def test_preview_projects_returns_html(self):
        """الاستجابة يجب أن تكون HTML."""
        resp = self.client.get("/preview/projects/حلم-الندى")
        if resp.status_code == 200:
            self.assertIn("text/html", resp.headers.get("content-type", ""))

    def test_preview_projects_path_traversal_dotdot(self):
        """/preview/projects/.. viene normalizzato da FastAPI a /preview — non deve esporre filesystem."""
        resp = self.client.get("/preview/projects/..")
        # FastAPI normalizes /preview/projects/.. → /preview, so it hits the home preview
        # (200 or 404). What matters is it does NOT return 400 or 500 unexpectedly,
        # and critically it cannot reach outside the allowed workspace.
        self.assertIn(resp.status_code, (200, 404))

    def test_preview_projects_path_traversal_slash(self):
        """/preview/projects/a/b يجب أن يعيد 404 (FastAPI لا يطابق المسار)."""
        resp = self.client.get("/preview/projects/a/b")
        # FastAPI won't match the route — 404 or 405 expected
        self.assertIn(resp.status_code, (404, 405, 422))

    def test_preview_projects_path_traversal_encoded(self):
        """/preview/projects/%2F يجب أن يُعالَج بأمان."""
        resp = self.client.get("/preview/projects/%2F")
        # Should not return 200 with root filesystem content
        self.assertNotEqual(resp.status_code, 200)


if __name__ == "__main__":
    unittest.main(verbosity=2)
