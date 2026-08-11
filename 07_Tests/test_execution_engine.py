import importlib.util
import os
import sys
import tempfile
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MODULE_PATH = os.path.join(ROOT, "06_Code", "executive_brain.py")

spec = importlib.util.spec_from_file_location("executive_brain", MODULE_PATH)
executive_brain = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = executive_brain
spec.loader.exec_module(executive_brain)

ExecutiveBrain = executive_brain.ExecutiveBrain


class ExecutionEngineTests(unittest.TestCase):
    def _plan(self, steps):
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
                "steps": steps,
                "selected_agent": "project_agent",
                "supporting_agents": [],
                "agent_reasoning": "",
                "guardian_status": "pass",
                "guardian_reason": "",
                "autonomy_level": "act_autonomously",
                "should_remember": False,
                "memory_note": None,
                "executive_message": "",
            },
        )()

    def _prepare_workspace(self, root):
        web_root = os.path.join(root, "09_Assets", "web")
        os.makedirs(os.path.join(web_root, "modules"), exist_ok=True)
        os.makedirs(os.path.join(web_root, "modules", "system"), exist_ok=True)
        with open(os.path.join(web_root, "index.html"), "w", encoding="utf-8") as handle:
            handle.write(
                "<div class=\"content\">\n"
                "        <div id=\"view-system\" class=\"page-view\">\n"
                "          <div id=\"systemContent\"></div>\n"
                "        </div>\n"
                "      </div>\n\n"
                "      <div class=\"composer\">\n"
            )
        with open(os.path.join(web_root, "modules", "shell.js"), "w", encoding="utf-8") as handle:
            handle.write(
                "const navItems = [\n"
                "    { key: 'system', label: 'System', icon: '⚙️' }\n"
                "  ];\n"
                "const pageMap = {\n"
                "      system: ['System', 'Ameer OS · النظام']\n"
                "    };\n"
            )
        with open(os.path.join(web_root, "modules", "loader.js"), "w", encoding="utf-8") as handle:
            handle.write(
                "const modulePaths = {\n"
                "    system: './modules/system/index.js'\n"
                "  };\n"
                "const hostIds = {\n"
                "    system: 'systemContent'\n"
                "  };\n"
            )

    def test_memory_action_is_persisted(self):
        brain = ExecutiveBrain(normalize_fn=lambda x: x)
        plan = type(
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
                "steps": ["remember", "save"],
                "selected_agent": "memory_agent",
                "supporting_agents": [],
                "agent_reasoning": "",
                "guardian_status": "pass",
                "guardian_reason": "",
                "autonomy_level": "act_autonomously",
                "should_remember": True,
                "memory_note": "remember this",
                "executive_message": "",
            },
        )()

        with tempfile.TemporaryDirectory() as tmpdir:
            result = brain._execute_plan(
                "تذكر أنني أحب العمل في الليل",
                plan,
                workspace_root=tmpdir,
            )

        self.assertTrue(result["memory"]["saved"])
        self.assertIn("04_Memory", result["memory"]["file"])

    def test_file_operation_creates_markdown_file(self):
        # Legacy direct path is now CLOSED — file.create must route through
        # ToolDispatcher.  _execute_plan / _create_file no longer writes directly;
        # the file result carries status "blocked" with the canonical reason.
        brain = ExecutiveBrain(normalize_fn=lambda x: x)
        plan = self._plan(["create file"])

        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, "04_Memory"), exist_ok=True)
            result = brain._execute_plan(
                "أنشئ ملفًا باسم 04_Memory/notes.md يحتوي على مرحبا",
                plan,
                workspace_root=tmpdir,
            )

            file_result = result["file"]
            self.assertEqual(file_result["status"], "blocked")
            self.assertEqual(file_result["reason"], "file_create_requires_tool_dispatcher")
            # No file must have been written to disk
            self.assertFalse(os.path.exists(file_result["path"]))

    def test_workspace_page_creation_updates_site_navigation_and_loader(self):
        brain = ExecutiveBrain(normalize_fn=lambda x: x)
        plan = self._plan(["create website page"])

        with tempfile.TemporaryDirectory() as tmpdir:
            self._prepare_workspace(tmpdir)
            result = brain._execute_plan(
                "أنشئ صفحة جديدة باسم services أضفها للموقع وحدّث التنقل",
                plan,
                workspace_root=tmpdir,
            )

            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["execution"]["status"], "completed")
            self.assertTrue(os.path.exists(os.path.join(tmpdir, "09_Assets", "web", "modules", "services", "index.js")))
            self.assertTrue(os.path.exists(os.path.join(tmpdir, "09_Assets", "web", "index.html")))
            self.assertTrue(any(item["name"] == "workspace_page_files_exist" for item in result["verification"]))

            with open(os.path.join(tmpdir, "09_Assets", "web", "modules", "shell.js"), "r", encoding="utf-8") as handle:
                shell_content = handle.read()
            self.assertIn("services", shell_content)

            with open(os.path.join(tmpdir, "09_Assets", "web", "modules", "loader.js"), "r", encoding="utf-8") as handle:
                loader_content = handle.read()
            self.assertIn("./modules/services/index.js", loader_content)

            with open(os.path.join(tmpdir, "09_Assets", "web", "modules", "services", "index.js"), "r", encoding="utf-8") as handle:
                module_content = handle.read()
            self.assertIn('data-action="ask-page"', module_content)
            self.assertIn('AmeerWorkspaceShell.sendPrompt', module_content)
            self.assertIn("AmeerWorkspaceShell.openPage", module_content)

    def test_path_traversal_is_blocked(self):
        brain = ExecutiveBrain(normalize_fn=lambda x: x)
        plan = self._plan(["create file"])

        with tempfile.TemporaryDirectory() as tmpdir:
            result = brain._execute_plan(
                "أنشئ ملفًا باسم ../../etc/passwd يحتوي على evil",
                plan,
                workspace_root=tmpdir,
            )
            # Either blocked outright or the file must remain inside tmpdir.
            if result.get("file"):
                file_status = result["file"].get("status", "")
                if file_status == "blocked":
                    self.assertEqual(file_status, "blocked")
                else:
                    # If a path was resolved, it must be inside tmpdir.
                    file_path = result["file"].get("path", "")
                    self.assertTrue(
                        os.path.abspath(file_path).startswith(os.path.abspath(tmpdir)),
                        f"Path escapes workspace: {file_path}",
                    )

    def test_write_outside_allowed_dirs_is_blocked(self):
        brain = ExecutiveBrain(normalize_fn=lambda x: x)
        plan = self._plan(["create file"])

        with tempfile.TemporaryDirectory() as tmpdir:
            result = brain._execute_plan(
                "أنشئ ملفًا باسم secret.md يحتوي على data",
                plan,
                workspace_root=tmpdir,
            )
            self.assertIsNotNone(result.get("file"))
            self.assertEqual(result["file"]["status"], "blocked",
                             "Writing to workspace root should be blocked by governance policy")

    def test_conversational_file_read_request_does_not_execute_direct_read(self):
        brain = ExecutiveBrain(normalize_fn=lambda x: x)
        plan = type(
            "Plan",
            (),
            {
                "request_type": "question",
                "ambiguous": False,
                "clarification_needed": False,
                "clarification_question": None,
                "context_links": [],
                "context_summary": "",
                "plan_type": "single_step",
                "steps": ["read file"],
                "selected_agent": "research_agent",
                "supporting_agents": [],
                "agent_reasoning": "",
                "guardian_status": "pass",
                "guardian_reason": "",
                "autonomy_level": "advice_only",
                "should_remember": False,
                "memory_note": None,
                "executive_message": "",
            },
        )()

        with tempfile.TemporaryDirectory() as tmpdir:
            target = os.path.join(tmpdir, "09_Assets", "runtime_workspace", "home")
            os.makedirs(target, exist_ok=True)
            with open(os.path.join(target, "secret.txt"), "w", encoding="utf-8") as handle:
                handle.write("secret-content")

            result = brain._execute_plan(
                "اقرأ ملف 09_Assets/runtime_workspace/home/secret.txt",
                plan,
                workspace_root=tmpdir,
            )

            self.assertEqual(result["file"]["status"], "blocked")
            self.assertEqual(result["file"]["reason"], "file_read_requires_tool_dispatcher")
            self.assertEqual(result["file"]["content_preview"], "")
            self.assertNotIn("file.create", result["tool_calls"])


if __name__ == "__main__":
    unittest.main()
