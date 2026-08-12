import os
import sys
import unittest
from dataclasses import FrozenInstanceError
from types import MappingProxyType


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CODE_ROOT = os.path.join(ROOT, "06_Code")
if CODE_ROOT not in sys.path:
    sys.path.insert(0, CODE_ROOT)

from kernel.tool_registry import ToolDefinition, ToolRegistry


class ToolRegistryTests(unittest.TestCase):
    def setUp(self):
        self.registry = ToolRegistry()

    def test_registered_tool_returns_correct_definition(self):
        tool = self.registry.get("file.read")
        self.assertEqual(tool.tool_name, "file.read")
        self.assertEqual(tool.capability, "file_operations")
        self.assertEqual(tool.action, "read")
        self.assertEqual(tool.risk_level, "low")
        self.assertEqual(tool.status, "enabled")

    def test_unknown_tool_is_rejected(self):
        with self.assertRaises(KeyError):
            self.registry.get("file.delete")

    def test_caller_cannot_override_registry_owned_metadata(self):
        with self.assertRaises(ValueError):
            self.registry.resolve(
                "file.create",
                {"target": "page.html", "content": "safe", "risk_level": "low"},
            )
        tool = self.registry.resolve("file.create", {"target": "page.html", "content": "safe"})
        self.assertEqual(tool.capability, "file_operations")
        self.assertEqual(tool.action, "write")
        self.assertEqual(tool.risk_level, "medium")

    def test_file_read_scope_is_registry_owned(self):
        tool = self.registry.get("file.read")
        self.assertEqual(tool.input_policy["scope_kind"], "runtime_workspace_only")
        self.assertEqual(tool.input_policy["scope_root"], "09_Assets/runtime_workspace")
        self.assertFalse(tool.input_policy["caller_scope_override"])
        self.assertTrue(tool.input_policy["resolve_symlinks"])
        with self.assertRaises(ValueError):
            self.registry.resolve(
                "file.read",
                {"target": "09_Assets/runtime_workspace/home/index.html", "scope_root": "/tmp/evil"},
            )

    def test_incomplete_or_invalid_definitions_are_rejected(self):
        with self.assertRaises(TypeError):
            ToolDefinition(
                tool_name="file.invalid",
                capability="file_operations",
                action="read",
                risk_level="low",
                input_policy={"required": ()},
            )
        with self.assertRaises(ValueError):
            ToolDefinition(
                tool_name="",
                capability="file_operations",
                action="read",
                risk_level="low",
                input_policy={"required": ()},
                output_policy={"content": "sanitized"},
            )
        with self.assertRaises(ValueError):
            ToolDefinition(
                tool_name="file.invalid",
                capability="file_operations",
                action="read",
                risk_level="critical",
                input_policy={"required": ()},
                output_policy={"content": "sanitized"},
            )
        with self.assertRaises(ValueError):
            ToolDefinition(
                tool_name="file.invalid",
                capability="file_operations",
                action="read",
                risk_level="low",
                input_policy={},
                output_policy={"content": "sanitized"},
            )

    def test_definitions_are_immutable_and_registry_does_not_execute_tools(self):
        tool = self.registry.get("file.create")
        self.assertIsInstance(tool.input_policy, MappingProxyType)
        with self.assertRaises(TypeError):
            tool.input_policy["required"] = ()
        with self.assertRaises(FrozenInstanceError):
            tool.action = "read"
        self.assertFalse(hasattr(self.registry, "execute"))
        self.assertIn("file.read", self.registry.list_tools())
        self.assertIn("file.create", self.registry.list_tools())
        self.assertIn("shell.run", self.registry.list_tools())


if __name__ == "__main__":
    unittest.main()
