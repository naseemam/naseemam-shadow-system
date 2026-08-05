import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CODE_ROOT = os.path.join(ROOT, "06_Code")
if CODE_ROOT not in sys.path:
    sys.path.insert(0, CODE_ROOT)

from executive_orchestrator.orchestrator import ExecutiveOrchestrator


class StubFounderLayer:
    def retrieve(self, query):
        return [{"content": "Founder vision: growth with clarity."}]


class StubKnowledgeGateway:
    def retrieve(self, query):
        return [{"content": "Project knowledge about launch readiness."}]


class StubDocumentLibrary:
    def search(self, query):
        return [{"title": "Project doc", "content": "Launch checklist", "approval_status": "trusted"}]

    def get_trusted_documents(self):
        return []


class StubToolBus:
    def __init__(self):
        self.calls = []

    def route(self, invocation):
        self.calls.append(invocation)
        return type("Result", (), {"success": True, "data": {"entries": [{"title": "GitHub PR"}]}})()


class ExecutiveOrchestratorTests(unittest.TestCase):
    def test_founder_routing(self):
        orchestrator = ExecutiveOrchestrator(founder_intelligence=StubFounderLayer())
        context = orchestrator.orchestrate("What is the founder's vision?", {})
        self.assertEqual(context.route, "founder_intelligence")
        self.assertTrue(context.excerpts)

    def test_knowledge_routing(self):
        orchestrator = ExecutiveOrchestrator(knowledge_gateway=StubKnowledgeGateway())
        context = orchestrator.orchestrate("What project knowledge should I know?", {})
        self.assertEqual(context.route, "knowledge_engine")
        self.assertTrue(context.excerpts)

    def test_github_routing(self):
        tool_bus = StubToolBus()
        orchestrator = ExecutiveOrchestrator(tool_bus=tool_bus)
        context = orchestrator.orchestrate("What is the status of PR #5?", {})
        self.assertEqual(context.route, "github_tool")
        self.assertEqual(context.capability, "pull_request.list")
        self.assertEqual(len(tool_bus.calls), 1)

    def test_railway_routing(self):
        tool_bus = StubToolBus()
        orchestrator = ExecutiveOrchestrator(tool_bus=tool_bus)
        context = orchestrator.orchestrate("What is the health of the production service?", {})
        self.assertEqual(context.route, "railway_tool")
        self.assertEqual(context.capability, "service.health")
        self.assertEqual(len(tool_bus.calls), 1)

    def test_unknown_request_fallback(self):
        orchestrator = ExecutiveOrchestrator()
        context = orchestrator.orchestrate("How is the weather today?", {})
        self.assertEqual(context.route, "fallback")
        self.assertEqual(context.source, "fallback")


if __name__ == "__main__":
    unittest.main()
