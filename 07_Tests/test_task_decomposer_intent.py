"""
Regression tests for TaskDecomposer intent detection.

Covers:
- "ابنِ الصفحة الرئيسية"  → build_homepage  (must not regress)
- "أنشئ صفحة عن حلم الندى" → build_generic   (new fix)
- "انشئ صفحة عن حلم الندى" → build_generic   (new fix)
- "اقرأ ملف .../home/index.html" → file_read  (file.read governed path)
  path tokens like home/index must NOT misroute a read command to build_homepage.
"""
import importlib.util
import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MODULE_PATH = os.path.join(ROOT, "06_Code", "kernel", "task_decomposer.py")

spec = importlib.util.spec_from_file_location("task_decomposer", MODULE_PATH)
task_decomposer = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = task_decomposer
spec.loader.exec_module(task_decomposer)

_detect_intent = task_decomposer._detect_intent
_extract_read_target = task_decomposer._extract_read_target
TaskDecomposer = task_decomposer.TaskDecomposer


class TestDetectIntentRegression(unittest.TestCase):

    def test_build_homepage_ibni(self):
        """ابنِ الصفحة الرئيسية → build_homepage (regression guard)"""
        self.assertEqual(_detect_intent("ابنِ الصفحة الرئيسية"), "build_homepage")

    def test_build_generic_anshi2_hulum_nada(self):
        """أنشئ صفحة عن حلم الندى → build_generic"""
        self.assertEqual(_detect_intent("أنشئ صفحة عن حلم الندى"), "build_generic")

    def test_build_generic_anshi_hulum_nada(self):
        """انشئ صفحة عن حلم الندى → build_generic"""
        self.assertEqual(_detect_intent("انشئ صفحة عن حلم الندى"), "build_generic")

    # ── file.read misrouting regression tests ────────────────────────────────
    # A read command whose path contains tokens like "home" or "index" must NOT
    # be routed to build_homepage and must remain executable as file_read.

    def test_read_home_index_arabic(self):
        """اقرأ ملف 09_Assets/runtime_workspace/home/index.html → file_read (not build_homepage)"""
        result = _detect_intent("اقرأ ملف 09_Assets/runtime_workspace/home/index.html")
        self.assertNotEqual(result, "build_homepage",
                            "read command with home/index path must not be misrouted to build_homepage")
        self.assertEqual(result, "file_read")

    def test_read_home_index_english(self):
        """read file 09_Assets/runtime_workspace/home/index.html → file_read"""
        result = _detect_intent("read file 09_Assets/runtime_workspace/home/index.html")
        self.assertNotEqual(result, "build_homepage")
        self.assertEqual(result, "file_read")

    def test_extract_read_target_after_definite_arabic_file_label(self):
        """اقرأ الملف AMEER_GUIDE.md must extract the filename, not «الملف»."""
        self.assertEqual(
            _extract_read_target("اقرأ الملف AMEER_GUIDE.md"),
            "AMEER_GUIDE.md",
        )

    def test_extract_read_target_after_plain_arabic_file_label(self):
        """اقرأ ملف AMEER_GUIDE.md remains supported."""
        self.assertEqual(
            _extract_read_target("اقرأ ملف AMEER_GUIDE.md"),
            "AMEER_GUIDE.md",
        )

    def test_show_home_index(self):
        """show home/index.html → file_read"""
        result = _detect_intent("show home/index.html")
        self.assertNotEqual(result, "build_homepage")
        self.assertEqual(result, "file_read")

    def test_read_landing_page_file(self):
        """read landing.html — contains HOME_PAGE_HINTS token but read wins"""
        result = _detect_intent("read landing.html")
        self.assertNotEqual(result, "build_homepage")
        self.assertEqual(result, "file_read")

    def test_build_homepage_still_works_no_read(self):
        """home — no read marker → still build_homepage"""
        self.assertEqual(_detect_intent("home"), "build_homepage")

    def test_build_homepage_index_no_read(self):
        """index — no read marker → still build_homepage"""
        self.assertEqual(_detect_intent("index"), "build_homepage")


class TestDecomposeIntentRegression(unittest.TestCase):
    """End-to-end via TaskDecomposer.decompose() — same assertions through public API."""

    def setUp(self):
        self.decomposer = TaskDecomposer(workspace_root=ROOT)

    def test_decompose_homepage(self):
        result = self.decomposer.decompose("ابنِ الصفحة الرئيسية")
        self.assertEqual(result["intent"], "build_homepage")
        self.assertGreater(result["task_count"], 0)

    def test_decompose_anshi2_hulum_nada(self):
        result = self.decomposer.decompose("أنشئ صفحة عن حلم الندى")
        self.assertEqual(result["intent"], "build_generic")
        self.assertGreater(result["task_count"], 0)

    def test_decompose_anshi_hulum_nada(self):
        result = self.decomposer.decompose("انشئ صفحة عن حلم الندى")
        self.assertEqual(result["intent"], "build_generic")
        self.assertGreater(result["task_count"], 0)

    def test_decompose_read_file_generates_governed_read_task(self):
        result = self.decomposer.decompose("اقرأ ملف 09_Assets/runtime_workspace/home/index.html")
        self.assertEqual(result["intent"], "file_read")
        self.assertEqual(result["task_count"], 1)
        self.assertEqual(result["tasks"][0]["action"], "read")
        self.assertEqual(result["tasks"][0]["executor"], "file")
        self.assertEqual(
            result["tasks"][0]["target"],
            "09_Assets/runtime_workspace/home/index.html",
        )

    def test_decompose_read_with_definite_file_label_generates_correct_target(self):
        result = self.decomposer.decompose("اقرأ الملف AMEER_GUIDE.md")
        self.assertEqual(result["intent"], "file_read")
        self.assertEqual(result["task_count"], 1)
        self.assertEqual(result["tasks"][0]["target"], "AMEER_GUIDE.md")


if __name__ == "__main__":
    unittest.main()
