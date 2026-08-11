from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CODE_ROOT = os.path.join(ROOT, "06_Code")

if CODE_ROOT not in sys.path:
    sys.path.insert(0, CODE_ROOT)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from kernel.executive_kernel import ExecutiveKernel


class AskFileReadPipelineTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._provider_patch = patch(
            "executive_brain.ExecutiveBrain._call_provider",
            return_value="رد تجريبي",
        )
        cls._provider_patch.start()

        from fastapi.testclient import TestClient
        import ameer_server

        cls.app_module = ameer_server
        cls.client = TestClient(ameer_server.app)

    @classmethod
    def tearDownClass(cls):
        cls._provider_patch.stop()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        runtime_home = self.root / "09_Assets" / "runtime_workspace" / "home"
        runtime_home.mkdir(parents=True, exist_ok=True)
        (self.root / ".ameer").mkdir(parents=True, exist_ok=True)
        self.target = runtime_home / "index.html"
        self.content = "<html><body>read-pipeline</body></html>"
        self.target.write_text(self.content, encoding="utf-8")

        self.kernel = ExecutiveKernel(self.root)
        self.originals = {
            "ROOT": self.app_module.ROOT,
            "KERNEL": self.app_module.KERNEL,
            "EXECUTION_BOUNDARY": self.app_module.EXECUTION_BOUNDARY,
            "DOCUMENTS": self.app_module.DOCUMENTS,
            "EXECUTIVE_CONVERSATION_ENGINE": self.app_module.EXECUTIVE_CONVERSATION_ENGINE,
        }
        self.app_module.ROOT = str(self.root)
        self.app_module.KERNEL = self.kernel
        self.app_module.EXECUTION_BOUNDARY = self.kernel.execution_boundary
        self.app_module.DOCUMENTS = []
        self.app_module.EXECUTIVE_CONVERSATION_ENGINE = None

    def tearDown(self):
        for key, value in self.originals.items():
            setattr(self.app_module, key, value)
        self.tmp.cleanup()

    def test_ask_file_read_returns_real_contents_without_build_misroute(self):
        before_paths = sorted(
            str(path.relative_to(self.root)).replace("\\", "/")
            for path in (self.root / "09_Assets" / "runtime_workspace").rglob("*")
            if path.is_file()
        )

        resp = self.client.post(
            "/ask",
            json={"query": "اقرأ ملف 09_Assets/runtime_workspace/home/index.html"},
        )

        self.assertEqual(resp.status_code, 200, resp.text)
        data = resp.json()
        self.assertEqual(data.get("reply"), self.content)

        trace = data.get("execution_trace") or {}
        pipeline = trace.get("pipeline") or []
        self.assertTrue(pipeline, f"missing pipeline trace: {trace}")
        self.assertEqual(pipeline[0].get("output", {}).get("intent"), "file_read")
        self.assertTrue(trace.get("final", {}).get("accepted"))
        self.assertEqual(trace.get("final", {}).get("completed"), 1)

        exec_results = trace.get("final", {}).get("results") or []
        self.assertEqual(len(exec_results), 1)
        self.assertEqual(exec_results[0].get("status"), "completed")
        self.assertEqual(exec_results[0].get("relative_path"), "09_Assets/runtime_workspace/home/index.html")
        self.assertEqual(exec_results[0].get("content"), self.content)

        after_paths = sorted(
            str(path.relative_to(self.root)).replace("\\", "/")
            for path in (self.root / "09_Assets" / "runtime_workspace").rglob("*")
            if path.is_file()
        )
        self.assertEqual(after_paths, before_paths)
        self.assertEqual(self.target.read_text(encoding="utf-8"), self.content)


if __name__ == "__main__":
    unittest.main()
