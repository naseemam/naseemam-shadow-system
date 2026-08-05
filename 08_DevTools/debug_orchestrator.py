import os
import sys

sys.path.insert(0, os.path.join(os.getcwd(), '06_Code'))
from executive_orchestrator.orchestrator import ExecutiveOrchestrator

class StubFounderLayer:
    def retrieve(self, query):
        return [{'content': 'Founder vision: growth with clarity.'}]

orchestrator = ExecutiveOrchestrator(founder_intelligence=StubFounderLayer())
print(orchestrator.orchestrate("What is the founder's vision?", {}))
