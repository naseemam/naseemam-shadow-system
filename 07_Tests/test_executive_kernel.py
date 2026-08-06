import importlib.util
import os
import sys
import unittest


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
KERNEL_PATH = os.path.join(ROOT, "06_Code", "executive_kernel.py")
TASK_PATH = os.path.join(ROOT, "06_Code", "task_contract.py")
ORCH_PATH = os.path.join(ROOT, "06_Code", "reasoning_orchestrator.py")
BRAIN_PATH = os.path.join(ROOT, "06_Code", "executive_brain.py")


def _load_module(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


executive_kernel_mod = _load_module("executive_kernel", KERNEL_PATH)
task_contract_mod = _load_module("task_contract", TASK_PATH)
reasoning_orchestrator_mod = _load_module("reasoning_orchestrator_for_kernel_test", ORCH_PATH)
executive_brain_mod = _load_module("executive_brain_for_kernel_test", BRAIN_PATH)

ExecutiveKernel = executive_kernel_mod.ExecutiveKernel
AmeerOrchestrator = reasoning_orchestrator_mod.AmeerOrchestrator
ExecutiveBrain = executive_brain_mod.ExecutiveBrain


class ExecutiveKernelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        docs = [
            {"path": "01_Docs/Master_Plan.md", "text": "Build the main website and home page."},
            {"path": "04_Memory/Founder.md", "text": "Naseem is the founder."},
        ]
        orchestrator = AmeerOrchestrator(
            documents=docs,
            score_fn=lambda query, text: 1 if any(word in text.lower() for word in ["website", "founder", "home"]) else 0,
            normalize_fn=lambda text: text.lower().strip(),
        )
        brain = ExecutiveBrain(normalize_fn=lambda text: text.lower().strip())
        cls.kernel = ExecutiveKernel(
            documents=docs,
            orchestrator=orchestrator,
            executive_brain=brain,
            task_batch_builder=task_contract_mod.build_execution_task_batch,
        )

    def test_execute_task_returns_task_batch_without_http(self):
        result = self.kernel.execute_task("أنشئ صفحة home")

        self.assertIn("plan", result)
        self.assertIn("task_batch", result)
        self.assertEqual(result["task_batch"]["task_count"], 1)
        self.assertEqual(result["task_batch"]["tasks"][0]["target"], "09_Assets/runtime_workspace/home/index.html")

    def test_analyze_and_execute_share_same_kernel(self):
        analysis = self.kernel.analyze("أنشئ صفحة home")
        execution = self.kernel.execute_task("أنشئ صفحة home")

        self.assertEqual(analysis["plan"].selected_agent, execution["plan"].selected_agent)
        self.assertEqual(analysis["orchestrator_result"]["intent"], execution["orchestrator_result"]["intent"])


if __name__ == "__main__":
    unittest.main()