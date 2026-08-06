import importlib.util
import json
import os
import sys
import tempfile
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MODULE_PATH = os.path.join(ROOT, "06_Code", "executive_brain.py")

spec = importlib.util.spec_from_file_location("executive_brain", MODULE_PATH)
executive_brain = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = executive_brain
assert spec.loader is not None
spec.loader.exec_module(executive_brain)

ExecutiveBrain = executive_brain.ExecutiveBrain
CAPABILITY_REGISTRY = executive_brain.CAPABILITY_REGISTRY


class PermissionPolicySystemTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._old_openai = os.environ.get("OPENAI_API_KEY")
        cls._old_ollama = os.environ.get("OLLAMA_ENABLED")
        os.environ.pop("OPENAI_API_KEY", None)
        os.environ["OLLAMA_ENABLED"] = "0"

    @classmethod
    def tearDownClass(cls):
        if cls._old_openai is None:
            os.environ.pop("OPENAI_API_KEY", None)
        else:
            os.environ["OPENAI_API_KEY"] = cls._old_openai
        if cls._old_ollama is None:
            os.environ.pop("OLLAMA_ENABLED", None)
        else:
            os.environ["OLLAMA_ENABLED"] = cls._old_ollama

    def _plan(self, guardian_status="pass", guardian_reason=""):
        return type(
            "Plan",
            (),
            {
                "request_type": "execution",
                "ambiguous": False,
                "clarification_needed": False,
                "clarification_question": None,
                "context_links": [],
                "context_summary": "",
                "plan_type": "multi_step",
                "steps": ["create file"],
                "selected_agent": "project_agent",
                "supporting_agents": [],
                "agent_reasoning": "",
                "guardian_status": guardian_status,
                "guardian_reason": guardian_reason,
                "autonomy_level": "act_autonomously",
                "should_remember": False,
                "memory_note": None,
                "executive_message": "",
            },
        )()

    def test_capability_registry_metadata_is_separate(self):
        self.assertIn("memory.save", CAPABILITY_REGISTRY)
        self.assertIn("system.destructive.execute", CAPABILITY_REGISTRY)
        self.assertEqual(CAPABILITY_REGISTRY["memory.save"]["permission_mode"], "policy")
        self.assertEqual(CAPABILITY_REGISTRY["system.destructive.execute"]["permission_mode"], "approval_required")

    def test_policy_permission_allows_memory_save(self):
        brain = ExecutiveBrain(normalize_fn=lambda x: x)
        with tempfile.TemporaryDirectory() as tmpdir:
            target = os.path.join(tmpdir, "04_Memory", "Preferences.md")
            decision = brain._authorize_execution_action(
                capability="memory.save",
                query="احفظ هذه المعلومة",
                plan=self._plan(),
                guardian_result={"status": "pass"},
                target_path=target,
                workspace_root=tmpdir,
            )

        self.assertTrue(decision["allowed"])
        self.assertEqual(decision["permission_source"], "policy")

    def test_approval_required_denied_without_explicit_founder_approval(self):
        brain = ExecutiveBrain(normalize_fn=lambda x: x)
        with tempfile.TemporaryDirectory() as tmpdir:
            decision = brain._authorize_execution_action(
                capability="system.destructive.execute",
                query="delete system state",
                plan=self._plan(),
                guardian_result={"status": "needs_approval", "approval_token": None},
                workspace_root=tmpdir,
            )

        self.assertFalse(decision["allowed"])
        self.assertIn(decision["decision"], {"needs_approval", "blocked"})

    def test_approval_required_allowed_with_explicit_founder_approval(self):
        brain = ExecutiveBrain(normalize_fn=lambda x: x)
        with tempfile.TemporaryDirectory() as tmpdir:
            decision = brain._authorize_execution_action(
                capability="system.destructive.execute",
                query="approved by founder for this action",
                plan=self._plan(),
                guardian_result={"status": "needs_approval", "approval_token": "founder_explicit_approval"},
                workspace_root=tmpdir,
            )

        self.assertTrue(decision["allowed"])
        self.assertEqual(decision["permission_source"], "approval_required")

    def test_permanent_permission_grant_is_reused(self):
        brain = ExecutiveBrain(normalize_fn=lambda x: x)
        with tempfile.TemporaryDirectory() as tmpdir:
            granted = brain._authorize_execution_action(
                capability="system.destructive.execute",
                query="approved by founder always allow this permanently",
                plan=self._plan(),
                guardian_result={"status": "needs_approval", "approval_token": "founder_explicit_approval"},
                workspace_root=tmpdir,
            )
            reused = brain._authorize_execution_action(
                capability="system.destructive.execute",
                query="run the same action",
                plan=self._plan(guardian_status="needs_approval", guardian_reason="sensitive"),
                guardian_result={"status": "needs_approval", "approval_token": None},
                workspace_root=tmpdir,
            )

        self.assertTrue(granted["allowed"])
        self.assertIsNotNone(granted.get("permanent_grant"))
        self.assertTrue(reused["allowed"])
        self.assertEqual(reused["permission_source"], "permanent")

    def test_execute_plan_blocks_unauthorized_action_and_collects_audit(self):
        brain = ExecutiveBrain(normalize_fn=lambda x: x)
        plan = self._plan(guardian_status="needs_approval", guardian_reason="sensitive")

        with tempfile.TemporaryDirectory() as tmpdir:
            result = brain._execute_plan(
                "أنشئ ملفًا باسم 04_Memory/secure.md يحتوي على data",
                plan,
                workspace_root=tmpdir,
                guardian_result={"status": "needs_approval", "approval_token": None},
            )

        self.assertIsNotNone(result.get("file"))
        self.assertEqual(result["file"].get("status"), "blocked")
        self.assertTrue(result.get("permission_audit"))
        self.assertIn(result["permission_audit"][0].get("decision"), {"needs_approval", "blocked"})

    def test_permission_audit_is_persisted(self):
        brain = ExecutiveBrain(normalize_fn=lambda x: x)
        plan = self._plan()

        with tempfile.TemporaryDirectory() as tmpdir:
            result = brain._execute_plan(
                "أنشئ ملفًا باسم 04_Memory/audit.md يحتوي على test",
                plan,
                workspace_root=tmpdir,
                guardian_result={"status": "pass"},
            )
            audit_file = os.path.join(tmpdir, ".ameer", "permission_audit.jsonl")

            self.assertTrue(os.path.exists(audit_file))
            with open(audit_file, "r", encoding="utf-8") as handle:
                lines = [line for line in handle.read().splitlines() if line.strip()]
            self.assertTrue(lines)
            entry = json.loads(lines[-1])
            self.assertIn("capability", entry)
            self.assertIn("decision", entry)

        self.assertTrue(result.get("permission_audit"))


if __name__ == "__main__":
    unittest.main()
