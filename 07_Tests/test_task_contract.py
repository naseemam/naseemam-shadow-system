import importlib.util
import os
import sys
import unittest


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MODULE_PATH = os.path.join(ROOT, "06_Code", "task_contract.py")

spec = importlib.util.spec_from_file_location("task_contract", MODULE_PATH)
task_contract = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = task_contract
assert spec.loader is not None
spec.loader.exec_module(task_contract)


class TaskContractTests(unittest.TestCase):
    def test_home_page_query_builds_sandboxed_html_task(self):
        task = task_contract.build_task_object("أنشئ صفحة home")

        self.assertEqual(task["action"], "create_file")
        self.assertEqual(task["executor"], "file")
        self.assertEqual(task["target"], "09_Assets/runtime_workspace/home/index.html")
        self.assertFalse(task["approval_required"])
        self.assertTrue(task["metadata"]["sandboxed"])
        self.assertIn("<html", task["inputs"]["content"].lower())

    def test_execution_batch_wraps_task_for_execute_endpoint(self):
        batch = task_contract.build_execution_task_batch("أنشئ صفحة home")

        self.assertTrue(batch["run_id"].startswith("run-"))
        self.assertEqual(batch["task_count"], 1)
        self.assertEqual(batch["sandbox_root"], "09_Assets/runtime_workspace")
        self.assertEqual(batch["tasks"][0]["target"], "09_Assets/runtime_workspace/home/index.html")


if __name__ == "__main__":
    unittest.main()