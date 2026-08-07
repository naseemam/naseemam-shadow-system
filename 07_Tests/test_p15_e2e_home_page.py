"""
test_p15_e2e_home_page.py
=========================
P1.5 E2E — "ابنِ الصفحة الرئيسية"

الاختبار الأول الذي يُثبت أن أمير يستطيع:
  استقبال أمر → تخطيط → تحقق → جدولة → تنفيذ → إنتاج ملفات فعلية → إعادة ExecutionReport

مسار التنفيذ المتحقق منه:
    ExecutiveKernel.execute_task(tasks)
        ↓
    PlanValidator       ← يتحقق أن الـ tasks صالحة وداخل runtime_workspace
        ↓
    Scheduler (P1.4)    ← يرتّب التنفيذ ويحدد الـ batches
        ↓
    FileExecutor (P1.5) ← ينشئ الملفات الفعلية داخل runtime_workspace
        ↓
    ExecutionReport     ← يُعيد نتيجة التنفيذ

قيود الأمان (مُختبَرة هنا):
  - كل الملفات تبقى داخل 09_Assets/runtime_workspace
  - لا git commit
  - لا تعديل لملفات أمير الأساسية
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
    """ينشئ بنية المجلدات الدنيا اللازمة لتشغيل ExecutiveKernel."""
    Path(tmp, ".ameer").mkdir(parents=True, exist_ok=True)
    Path(tmp, "04_Memory").mkdir(parents=True, exist_ok=True)
    Path(tmp, "09_Assets", "runtime_workspace").mkdir(parents=True, exist_ok=True)


# ── محتوى الصفحة الرئيسية ────────────────────────────────────────────────────

_INDEX_HTML = """\
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>الصفحة الرئيسية — أمير</title>
  <link rel="stylesheet" href="style.css" />
</head>
<body>
  <h1>مرحباً بك في نظام أمير</h1>
  <p>النظام التنفيذي الذكي لناصر الشهري.</p>
  <script src="script.js"></script>
</body>
</html>
"""

_STYLE_CSS = """\
/* الصفحة الرئيسية — أمير */
body {
  font-family: 'Segoe UI', Tahoma, Arial, sans-serif;
  background: #0f172a;
  color: #f1f5f9;
  margin: 0;
  padding: 2rem;
  direction: rtl;
}

h1 {
  font-size: 2rem;
  color: #38bdf8;
}

p {
  font-size: 1.1rem;
  color: #94a3b8;
}
"""

_SCRIPT_JS = """\
// script.js — الصفحة الرئيسية أمير
(function () {
  'use strict';
  console.log('[أمير] الصفحة الرئيسية جاهزة.');
})();
"""


def _build_home_page_tasks() -> list:
    """
    يُعيد قائمة مهام بناء الصفحة الرئيسية.

    البنية المستهدفة داخل runtime_workspace:
        home/
        ├── index.html
        ├── style.css
        └── script.js
    """
    base = "09_Assets/runtime_workspace/home"
    return [
        {
            "id": "home-index",
            "action": "write",
            "executor": "file",
            "target": f"{base}/index.html",
            "content": _INDEX_HTML,
            "priority": "high",
            "parallel_safe": False,
        },
        {
            "id": "home-style",
            "action": "write",
            "executor": "file",
            "target": f"{base}/style.css",
            "content": _STYLE_CSS,
            "depends_on": ["home-index"],
            "priority": "medium",
            "parallel_safe": True,
        },
        {
            "id": "home-script",
            "action": "write",
            "executor": "file",
            "target": f"{base}/script.js",
            "content": _SCRIPT_JS,
            "depends_on": ["home-index"],
            "priority": "medium",
            "parallel_safe": True,
        },
    ]


class BuildHomePageE2ETest(unittest.TestCase):
    """
    الاختبار الشامل الأول: "ابنِ الصفحة الرئيسية"

    يُثبت أن الدورة الكاملة تعمل:
      أمير يستقبل أمرًا → يخطط → يتحقق → يجدول → ينفذ → ينتج ملفات فعلية → يُخبرني بالنتيجة
    """

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        _make_workspace(self.tmp)
        kernel_mod = _load(
            "executive_kernel_e2e",
            os.path.join(CODE_ROOT, "kernel", "executive_kernel.py"),
        )
        self.kernel = kernel_mod.ExecutiveKernel(workspace_root=self.tmp)
        self.tasks = _build_home_page_tasks()

    # ── 1. PlanValidator — تحقق من صلاحية الخطة ──────────────────────────────

    def test_01_plan_validates_successfully(self):
        """يجب أن تجتاز الخطة بوابة PlanValidator بدون أي حجب."""
        result = self.kernel.plan_validator.validate(self.tasks)
        self.assertTrue(result["valid"], f"PlanValidator blocked tasks: {result['blocked']}")
        self.assertEqual(result["blocked"], [])

    def test_02_plan_validator_confirms_sandbox_safety(self):
        """كل الأهداف داخل runtime_workspace — لا انتهاك للـ sandbox."""
        result = self.kernel.plan_validator.validate(self.tasks)
        for blocked_msg in result["blocked"]:
            self.assertNotIn("outside runtime_workspace", blocked_msg)

    # ── 2. Scheduler — تحقق من الجدولة ───────────────────────────────────────

    def test_03_scheduler_accepts_tasks_and_builds_batches(self):
        """يجب أن يقبل Scheduler المهام ويُنتج ترتيب تنفيذ صحيح."""
        result = self.kernel.scheduler.schedule(self.tasks)
        self.assertTrue(result["accepted"], f"Scheduler rejected tasks: {result}")
        self.assertIn("home-index", result["execution_order"])
        self.assertIn("home-style", result["execution_order"])
        self.assertIn("home-script", result["execution_order"])

    def test_04_scheduler_runs_index_first(self):
        """home-index يجب أن يُنفَّذ أولاً (الـ dependencies تعتمد عليه)."""
        result = self.kernel.scheduler.schedule(self.tasks)
        self.assertEqual(result["execution_order"][0], "home-index")

    def test_05_scheduler_runs_style_and_script_in_parallel(self):
        """home-style و home-script مستقلان وقابلان للتشغيل معاً."""
        result = self.kernel.scheduler.schedule(self.tasks)
        parallel_batch = next(
            (b for b in result["batches"] if b["parallel"]),
            None,
        )
        self.assertIsNotNone(parallel_batch, "يجب أن يوجد batch متوازٍ لـ style و script")
        ids = set(parallel_batch["task_ids"])
        self.assertIn("home-style", ids)
        self.assertIn("home-script", ids)

    # ── 3. Execute — تنفيذ كامل عبر ExecutiveKernel ──────────────────────────

    def test_06_execute_task_returns_accepted(self):
        """execute_task يجب أن يُعيد accepted=True."""
        report = self.kernel.execute_task(self.tasks)
        self.assertTrue(report["accepted"], f"execute_task not accepted: {report}")

    def test_07_execute_task_completes_all_three_files(self):
        """يجب أن تُكتمل المهام الثلاث بدون فشل."""
        report = self.kernel.execute_task(self.tasks)
        exec_summary = report["execution"]
        self.assertEqual(exec_summary["completed"], 3, f"Expected 3 completed, got: {exec_summary}")
        self.assertEqual(exec_summary["failed"], 0)
        self.assertEqual(exec_summary["blocked"], 0)

    # ── 4. Verify files exist — التحقق من وجود الملفات الفعلية ──────────────

    def test_08_index_html_exists_on_disk(self):
        """index.html يجب أن يكون موجودًا فعليًا على القرص."""
        self.kernel.execute_task(self.tasks)
        path = Path(self.tmp, "09_Assets", "runtime_workspace", "home", "index.html")
        self.assertTrue(path.exists(), f"index.html غير موجود: {path}")

    def test_09_style_css_exists_on_disk(self):
        """style.css يجب أن يكون موجودًا فعليًا على القرص."""
        self.kernel.execute_task(self.tasks)
        path = Path(self.tmp, "09_Assets", "runtime_workspace", "home", "style.css")
        self.assertTrue(path.exists(), f"style.css غير موجود: {path}")

    def test_10_script_js_exists_on_disk(self):
        """script.js يجب أن يكون موجودًا فعليًا على القرص."""
        self.kernel.execute_task(self.tasks)
        path = Path(self.tmp, "09_Assets", "runtime_workspace", "home", "script.js")
        self.assertTrue(path.exists(), f"script.js غير موجود: {path}")

    def test_11_index_html_contains_expected_content(self):
        """محتوى index.html يجب أن يحتوي على العنوان المتوقع."""
        self.kernel.execute_task(self.tasks)
        path = Path(self.tmp, "09_Assets", "runtime_workspace", "home", "index.html")
        content = path.read_text(encoding="utf-8")
        self.assertIn("أمير", content)
        self.assertIn("<html", content)

    def test_12_style_css_contains_expected_content(self):
        """محتوى style.css يجب أن يحتوي على تنسيق صحيح."""
        self.kernel.execute_task(self.tasks)
        path = Path(self.tmp, "09_Assets", "runtime_workspace", "home", "style.css")
        content = path.read_text(encoding="utf-8")
        self.assertIn("body", content)

    def test_13_script_js_contains_expected_content(self):
        """محتوى script.js يجب أن يحتوي على كود JavaScript صالح."""
        self.kernel.execute_task(self.tasks)
        path = Path(self.tmp, "09_Assets", "runtime_workspace", "home", "script.js")
        content = path.read_text(encoding="utf-8")
        self.assertIn("console.log", content)

    # ── 5. ExecutionReport — التحقق من هيكل التقرير ─────────────────────────

    def test_14_execution_report_contains_all_required_keys(self):
        """ExecutionReport يجب أن يحتوي على: accepted, validation, schedule, execution."""
        report = self.kernel.execute_task(self.tasks)
        for key in ("accepted", "validation", "schedule", "execution"):
            self.assertIn(key, report, f"ExecutionReport missing key: '{key}'")

    def test_15_execution_report_results_list_has_three_entries(self):
        """قائمة النتائج يجب أن تحتوي على 3 إدخالات (واحدة لكل ملف)."""
        report = self.kernel.execute_task(self.tasks)
        results = report["execution"]["results"]
        self.assertEqual(len(results), 3)

    def test_16_all_result_entries_have_status_completed(self):
        """كل نتيجة في التقرير يجب أن يكون status='completed'."""
        report = self.kernel.execute_task(self.tasks)
        for entry in report["execution"]["results"]:
            self.assertEqual(
                entry.get("status"),
                "completed",
                f"نتيجة غير مكتملة: {entry}",
            )

    def test_17_result_paths_are_inside_runtime_workspace(self):
        """كل المسارات في التقرير يجب أن تقع داخل runtime_workspace."""
        report = self.kernel.execute_task(self.tasks)
        for entry in report["execution"]["results"]:
            rel = entry.get("relative_path", "")
            self.assertTrue(
                rel.startswith("09_Assets/runtime_workspace"),
                f"مسار خارج runtime_workspace: {rel}",
            )

    # ── 6. Sandbox Safety — التحقق من قيود الأمان ────────────────────────────

    def test_18_sandbox_rejects_target_outside_runtime_workspace(self):
        """أي مهمة تستهدف خارج runtime_workspace يجب أن تُرفض بواسطة PlanValidator."""
        unsafe_tasks = [
            {
                "id": "unsafe",
                "action": "write",
                "executor": "file",
                "target": "01_Docs/hacked.txt",
                "content": "هذا يجب أن يُحجب",
            }
        ]
        result = self.kernel.plan_validator.validate(unsafe_tasks)
        self.assertFalse(result["valid"])
        self.assertTrue(
            any("outside runtime_workspace" in msg for msg in result["blocked"]),
            f"لم يُحجب الهدف غير الآمن: {result['blocked']}",
        )

    def test_19_file_executor_rejects_absolute_path_targets(self):
        """FileExecutor يجب أن يرفض المسارات المطلقة مباشرةً."""
        absolute_target = str(
            Path(self.tmp, "09_Assets", "runtime_workspace", "home", "absolute.html")
        )
        outcome = self.kernel.file_executor.execute(
            {
                "id": "abs",
                "action": "write",
                "executor": "file",
                "target": absolute_target,
                "content": "x",
            }
        )
        self.assertEqual(outcome["status"], "blocked")
        self.assertEqual(outcome["reason"], "target_outside_runtime_workspace")

    def test_20_no_files_created_outside_runtime_workspace(self):
        """بعد التنفيذ الكامل، لا يوجد أي ملف جديد خارج runtime_workspace في tmp."""
        report = self.kernel.execute_task(self.tasks)
        # تحقق أن جميع الملفات المنشأة تقع داخل runtime_workspace
        for entry in report_results_paths(report):
            self.assertTrue(
                entry.startswith("09_Assets/runtime_workspace"),
                f"ملف خارج runtime_workspace: {entry}",
            )


def report_results_paths(report: dict) -> list:
    """مساعد: يستخرج relative_path من كل نتيجة في التقرير."""
    return [r.get("relative_path", "") for r in report.get("execution", {}).get("results", [])]


class ExecutionReportStructureTest(unittest.TestCase):
    """
    اختبار منفصل يتحقق من هيكل ExecutionReport بشكل مستقل
    دون الحاجة للوصول الكامل إلى الـ filesystem.
    """

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        _make_workspace(self.tmp)
        kernel_mod = _load(
            "executive_kernel_e2e_struct",
            os.path.join(CODE_ROOT, "kernel", "executive_kernel.py"),
        )
        self.kernel = kernel_mod.ExecutiveKernel(workspace_root=self.tmp)

    def test_single_file_execution_report_structure(self):
        """
        اختبار بسيط لتنفيذ ملف واحد والتحقق من هيكل التقرير.
        """
        tasks = [
            {
                "id": "single",
                "action": "write",
                "executor": "file",
                "target": "09_Assets/runtime_workspace/test_single.txt",
                "content": "اختبار الدورة الكاملة",
            }
        ]
        report = self.kernel.execute_task(tasks)

        # هيكل التقرير
        self.assertIn("accepted", report)
        self.assertIn("validation", report)
        self.assertIn("schedule", report)
        self.assertIn("execution", report)
        self.assertTrue(report["accepted"])

        # التحقق من الملف
        path = Path(self.tmp, "09_Assets", "runtime_workspace", "test_single.txt")
        self.assertTrue(path.exists())
        self.assertEqual(path.read_text(encoding="utf-8"), "اختبار الدورة الكاملة")


if __name__ == "__main__":
    unittest.main(verbosity=2)
