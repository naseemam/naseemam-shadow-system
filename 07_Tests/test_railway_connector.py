import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CODE_ROOT = os.path.join(ROOT, "06_Code")
if CODE_ROOT not in sys.path:
    sys.path.insert(0, CODE_ROOT)

from document_library.service import DocumentLibraryService
from railway_connector.connector import RailwayConnector
from tool_bus.bus import ExecutiveToolBus, ToolInvocation
from tool_bus.railway_tool import RailwayTool

MODULE_PATH = os.path.join(CODE_ROOT, "executive_brain.py")
import importlib.util

SPEC = importlib.util.spec_from_file_location("executive_brain", MODULE_PATH)
EXECUTIVE_BRAIN_MODULE = importlib.util.module_from_spec(SPEC)
sys.modules["executive_brain"] = EXECUTIVE_BRAIN_MODULE
assert SPEC.loader is not None
SPEC.loader.exec_module(EXECUTIVE_BRAIN_MODULE)
ExecutiveBrain = EXECUTIVE_BRAIN_MODULE.ExecutiveBrain


class StubRailwayClient:
    def get_service_health(self, project, service, environment):
        return {
            "status": "healthy",
            "health_score": 99,
            "project": project,
            "service": service,
            "environment": environment,
            "timestamp": "2026-08-05T12:00:00Z",
        }

    def get_latest_deployment(self, project, service, environment):
        return {
            "version": "v2.3.1",
            "status": "succeeded",
            "project": project,
            "service": service,
            "environment": environment,
            "timestamp": "2026-08-05T11:30:00Z",
        }

    def get_deployment_history(self, project, service, environment):
        return [
            {"version": "v2.3.1", "status": "succeeded", "timestamp": "2026-08-05T11:30:00Z"},
            {"version": "v2.3.0", "status": "succeeded", "timestamp": "2026-08-04T11:00:00Z"},
        ]

    def get_logs(self, project, service, environment):
        return [{"message": "request completed", "timestamp": "2026-08-05T12:01:00Z"}]

    def get_metrics(self, project, service, environment):
        return {
            "cpu_usage": 48.2,
            "memory_usage": 64.1,
            "error_rate": 0.2,
            "response_time_ms": 180,
            "timestamp": "2026-08-05T12:02:00Z",
        }


class RailwayConnectorTests(unittest.TestCase):
    def test_health_retrieval(self):
        connector = RailwayConnector(client=StubRailwayClient(), project="acme", service="api", environment="production")
        entries = connector.retrieve_service_health()
        self.assertTrue(entries)
        self.assertIn("healthy", entries[0].content.lower())
        self.assertIn("project: acme", entries[0].content.lower())

    def test_deployment_retrieval(self):
        connector = RailwayConnector(client=StubRailwayClient(), project="acme", service="api", environment="production")
        entries = connector.retrieve_latest_deployment()
        self.assertTrue(entries)
        self.assertIn("v2.3.1", entries[0].content)

    def test_metrics_retrieval(self):
        connector = RailwayConnector(client=StubRailwayClient(), project="acme", service="api", environment="production")
        entries = connector.retrieve_metrics()
        self.assertTrue(entries)
        self.assertEqual(len(entries), 4)
        self.assertTrue(any("cpu" in entry.title.lower() for entry in entries))

    def test_log_retrieval(self):
        connector = RailwayConnector(client=StubRailwayClient(), project="acme", service="api", environment="production")
        entries = connector.retrieve_logs()
        self.assertTrue(entries)
        self.assertIn("request completed", entries[0].content)

    def test_executive_brain_isolation(self):
        bus = ExecutiveToolBus()
        connector = RailwayConnector(client=StubRailwayClient(), project="acme", service="api", environment="production")
        tool = RailwayTool(connector)
        bus.register_tool(tool)

        result = bus.route(ToolInvocation(capability="service.health", payload={"project": "acme", "service": "api", "environment": "production"}))
        self.assertTrue(result.success)

        brain = ExecutiveBrain(normalize_fn=lambda x: x)
        plan = brain.think("What is the health of the production service?", [], guardian_result={"status": "pass", "reason": ""})
        self.assertNotIn("railway", plan.executive_message.lower())


if __name__ == "__main__":
    unittest.main()
