"""
test_ask_execute_pipeline.py
============================
اختبار تكاملي HTTP يتحقق من أن أمر «ابنِ الصفحة الرئيسية»
يمر من /ask → ExecutiveKernel.execute_command() كاملًا.

ما يتحقق منه:
  1. استقبال /ask يُعيد 200
  2. intent مُكتشَف = build_homepage
  3. execution_trace موجود في الرد
  4. final.accepted = True
  5. final.completed = 3
  6. الملفات الثلاثة موجودة فعليًا على القرص داخل runtime_workspace
  7. الرد يحتوي على رسالة نجاح (لا رسالة توضيح)
"""

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


class AskExecutePipelineTest(unittest.TestCase):
    """
    اختبار HTTP كامل: /ask → ExecutiveKernel.execute_command()

    يُعيد ameer_server.KERNEL إلى مجلد مؤقت حتى لا تُلوَّث
    runtime_workspace الحقيقية أثناء الاختبار.
    """

    @classmethod
    def setUpClass(cls):
        # Patch provider so tests work offline (no API key needed)
        cls._provider_patch = patch(
            "executive_brain.ExecutiveBrain._call_provider",
            return_value="رد تجريبي",
        )
        cls._provider_patch.start()

        from fastapi.testclient import TestClient
        import ameer_server

        cls.app_module = ameer_server
        cls.client = TestClient(ameer_server.app)

        # Redirect the kernel's workspace_root to a temp dir so file
        # creation is isolated and verifiable.
        cls.tmp = tempfile.mkdtemp()
        _tmp = Path(cls.tmp)
        (_tmp / ".ameer").mkdir(parents=True, exist_ok=True)
        (_tmp / "04_Memory").mkdir(parents=True, exist_ok=True)
        (_tmp / "09_Assets" / "runtime_workspace").mkdir(parents=True, exist_ok=True)

        if ameer_server.KERNEL:
            # Patch the kernel's workspace root for isolation
            ameer_server.KERNEL._root = _tmp
            ameer_server.KERNEL.file_executor._root = _tmp
            ameer_server.KERNEL.file_executor._runtime_workspace = (
                _tmp / "09_Assets" / "runtime_workspace"
            ).resolve()
            ameer_server.KERNEL.task_decomposer._root = str(_tmp)

        cls.kernel = ameer_server.KERNEL
        cls.workspace = _tmp

    @classmethod
    def tearDownClass(cls):
        cls._provider_patch.stop()

    # ── helpers ───────────────────────────────────────────────────────────────

    def _post_ask(self, query: str):
        return self.client.post("/ask", json={"query": query})

    # ── 1. HTTP status ────────────────────────────────────────────────────────

    def test_01_ask_returns_200(self):
        """يجب أن يُعيد /ask كود 200."""
        resp = self._post_ask("ابنِ الصفحة الرئيسية")
        self.assertEqual(resp.status_code, 200, resp.text)

    # ── 2. execution_trace present ────────────────────────────────────────────

    def test_02_execution_trace_present_in_response(self):
        """execution_trace يجب أن يكون موجودًا في جسم الرد."""
        if not self.kernel:
            self.skipTest("Kernel unavailable")
        resp = self._post_ask("ابنِ الصفحة الرئيسية")
        data = resp.json()
        self.assertIn(
            "execution_trace", data,
            f"execution_trace غير موجود في الرد. مفاتيح الرد: {list(data.keys())}",
        )

    # ── 3. intent detected ────────────────────────────────────────────────────

    def test_03_intent_detected_as_build_homepage(self):
        """intent يجب أن يُكتشَف بوصفه build_homepage."""
        if not self.kernel:
            self.skipTest("Kernel unavailable")
        resp = self._post_ask("ابنِ الصفحة الرئيسية")
        data = resp.json()
        trace = data.get("execution_trace", {})
        self.assertEqual(
            trace.get("final", {}).get("accepted") is not None,
            True,
            "execution_trace.final غير موجود",
        )
        # Check pipeline step 1 for intent
        pipeline = trace.get("pipeline", [])
        self.assertTrue(len(pipeline) > 0, "pipeline فارغ")
        step1 = pipeline[0]
        detected_intent = step1.get("output", {}).get("intent", "")
        self.assertEqual(
            detected_intent,
            "build_homepage",
            f"intent المكتشَف: '{detected_intent}' — المتوقع: 'build_homepage'",
        )

    # ── 4. accepted = True ────────────────────────────────────────────────────

    def test_04_execution_trace_accepted_true(self):
        """execution_trace.final.accepted يجب أن يكون True."""
        if not self.kernel:
            self.skipTest("Kernel unavailable")
        resp = self._post_ask("ابنِ الصفحة الرئيسية")
        data = resp.json()
        trace = data.get("execution_trace", {})
        final = trace.get("final", {})
        self.assertTrue(
            final.get("accepted"),
            f"final.accepted ليس True. final: {final}",
        )

    # ── 5. completed = 3 ──────────────────────────────────────────────────────

    def test_05_execution_trace_completed_equals_3(self):
        """final.completed يجب أن يساوي 3 (ثلاثة ملفات)."""
        if not self.kernel:
            self.skipTest("Kernel unavailable")
        resp = self._post_ask("ابنِ الصفحة الرئيسية")
        data = resp.json()
        trace = data.get("execution_trace", {})
        final = trace.get("final", {})
        self.assertEqual(
            final.get("completed"),
            3,
            f"final.completed = {final.get('completed')} — المتوقع: 3",
        )

    # ── 6. files exist on disk ────────────────────────────────────────────────

    def test_06_index_html_created_on_disk(self):
        """index.html يجب أن يُنشَأ فعليًا على القرص."""
        if not self.kernel:
            self.skipTest("Kernel unavailable")
        self._post_ask("ابنِ الصفحة الرئيسية")
        path = self.workspace / "09_Assets" / "runtime_workspace" / "home" / "index.html"
        self.assertTrue(path.exists(), f"index.html غير موجود: {path}")

    def test_07_style_css_created_on_disk(self):
        """style.css يجب أن يُنشَأ فعليًا على القرص."""
        if not self.kernel:
            self.skipTest("Kernel unavailable")
        self._post_ask("ابنِ الصفحة الرئيسية")
        path = self.workspace / "09_Assets" / "runtime_workspace" / "home" / "style.css"
        self.assertTrue(path.exists(), f"style.css غير موجود: {path}")

    def test_08_script_js_created_on_disk(self):
        """script.js يجب أن يُنشَأ فعليًا على القرص."""
        if not self.kernel:
            self.skipTest("Kernel unavailable")
        self._post_ask("ابنِ الصفحة الرئيسية")
        path = self.workspace / "09_Assets" / "runtime_workspace" / "home" / "script.js"
        self.assertTrue(path.exists(), f"script.js غير موجود: {path}")

    # ── 7. reply confirms success (not clarification) ─────────────────────────

    def test_09_reply_confirms_execution_not_clarification(self):
        """رد أمير يجب أن يؤكد نجاح البناء، لا يطلب توضيحًا."""
        if not self.kernel:
            self.skipTest("Kernel unavailable")
        resp = self._post_ask("ابنِ الصفحة الرئيسية")
        data = resp.json()
        reply = data.get("reply") or data.get("message") or ""
        # The reply must NOT be a clarification question
        self.assertNotIn(
            "قبل أن أكمل",
            reply,
            f"أمير طلب توضيحًا بدل التنفيذ: {reply!r}",
        )
        # The reply should mention success
        has_success_signal = any(
            token in reply
            for token in ["✅", "تم", "بنجاح", "أُنشئ", "Preview", "معاينة", "ملفات"]
        )
        self.assertTrue(
            has_success_signal,
            f"الرد لا يحتوي على إشارة نجاح. الرد: {reply!r}",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
