"""
Regression tests for TaskDecomposer intent detection.

Covers:
- "ابنِ الصفحة الرئيسية"  → build_homepage  (must not regress)
- "أنشئ صفحة عن حلم الندى" → build_generic   (new fix)
- "انشئ صفحة عن حلم الندى" → build_generic   (new fix)
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


if __name__ == "__main__":
    unittest.main()
