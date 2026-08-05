import os
import sys

sys.path.insert(0, os.path.join(os.getcwd(), '06_Code'))

from executive_brain import ExecutiveBrain
from executive_orchestrator.orchestrator import ExecutiveContext


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
        self.calls.append(invocation.capability)
        if invocation.capability == "pull_request.list":
            return type("Result", (), {"success": True, "data": {"entries": [{"title": "PR #5"}]}})()
        if invocation.capability == "service.health":
            return type("Result", (), {"success": True, "data": {"entries": [{"title": "Railway health"}]}})()
        return type("Result", (), {"success": True, "data": {"entries": [{"title": "Demo"}]}})()


brain = ExecutiveBrain(
    normalize_fn=lambda x: x,
    founder_intelligence=StubFounderLayer(),
    knowledge_gateway=StubKnowledgeGateway(),
    document_library=StubDocumentLibrary(),
    tool_bus=StubToolBus(),
)

scenarios = [
    ("Greeting", "Hello there"),
    ("Founder strategy", "What is the founder's vision?"),
    ("Project knowledge", "What project knowledge should I know?"),
    ("GitHub operational", "What is the status of PR #5?"),
    ("Railway operational", "What is the health of the production service?"),
    ("Mixed multi-source", "What is the founder's vision and the current project knowledge?"),
    ("Unknown", "How is the weather today?"),
]

for name, query in scenarios:
    plan = brain.think(query, [], guardian_result={"status": "pass", "reason": ""})
    context = brain._orchestrator.orchestrate(query, {}) if brain._orchestrator else None
    print(f"{name}: route={getattr(context, 'route', 'n/a')} capability={getattr(context, 'capability', 'n/a')} context={plan.context_summary[:120].replace(chr(10), ' ')}")
