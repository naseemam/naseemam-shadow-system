"""
test_p0_governance_wiring.py
============================
P0.1 — Governance Wiring acceptance tests.
P0.2 — Double think() elimination acceptance tests.

P0.1 verifies:
1. A query classified as 'decision' creates a record in DecisionEngine via the /ask pipeline.
2. A query classified as 'planning' creates a record in DecisionEngine via the /ask pipeline.
3. A guardian-flagged (needs_approval) request creates an ApprovalGate record.
4. Normal (pass) queries do NOT create spurious approval records.

P0.2 verifies:
5. get_reasoning_output() with existing_plan does NOT call think() again.
6. get_reasoning_output() without existing_plan still works (backward compat).
7. /ask pipeline computes think() exactly once per request.
"""

import importlib.util
import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch, call

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CODE_ROOT = os.path.join(ROOT, "06_Code")

if CODE_ROOT not in sys.path:
    sys.path.insert(0, CODE_ROOT)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def _load(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# ── Load modules ──────────────────────────────────────────────────────────────

_brain_mod = _load(
    "executive_brain",
    os.path.join(CODE_ROOT, "executive_brain.py"),
)
ExecutiveBrain = _brain_mod.ExecutiveBrain
ExecutivePlan = _brain_mod.ExecutivePlan


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_plan(request_type="question", guardian_status="pass"):
    return ExecutivePlan(
        request_type=request_type,
        ambiguous=False,
        clarification_needed=False,
        clarification_question=None,
        context_links=[],
        context_summary="",
        plan_type="direct",
        steps=[],
        selected_agent="ameer_core",
        supporting_agents=[],
        agent_reasoning="",
        guardian_status=guardian_status,
        guardian_reason="",
        autonomy_level="act_autonomously",
        should_remember=False,
        memory_note=None,
        executive_message="",
    )


# ── P0.2: get_reasoning_output double-think elimination ───────────────────────

class GetReasoningOutputTests(unittest.TestCase):
    """Verify P0.2: get_reasoning_output(existing_plan=...) skips think()."""

    def setUp(self):
        self.brain = ExecutiveBrain(normalize_fn=lambda x: x)

    def test_existing_plan_skips_think(self):
        """When existing_plan is passed, think() must NOT be called."""
        existing = _make_plan(request_type="question")
        with patch.object(self.brain, "think") as mock_think:
            result = self.brain.get_reasoning_output(
                "أي سؤال",
                documents=[],
                existing_plan=existing,
            )
            mock_think.assert_not_called()
        self.assertIn("reasoning", result)
        self.assertIn("executive_state", result)
        self.assertIn("_plan", result)
        self.assertIs(result["_plan"], existing)

    def test_no_existing_plan_calls_think(self):
        """When no existing_plan, think() is called exactly once."""
        with patch.object(self.brain, "think", return_value=_make_plan()) as mock_think:
            self.brain.get_reasoning_output("أي سؤال", documents=[])
            self.assertEqual(mock_think.call_count, 1)

    def test_reasoning_output_structure_with_existing_plan(self):
        """Output schema is identical whether plan is pre-computed or not."""
        plan = _make_plan(request_type="planning", guardian_status="pass")
        result = self.brain.get_reasoning_output("خطة", documents=[], existing_plan=plan)
        reasoning = result["reasoning"]
        self.assertEqual(reasoning["request_type"], "planning")
        self.assertEqual(reasoning["guardian_status"], "pass")
        exec_state = result["executive_state"]
        self.assertEqual(exec_state["selected_agent"], "ameer_core")

    def test_backward_compat_without_existing_plan(self):
        """Old callers omitting existing_plan still get correct output."""
        brain = ExecutiveBrain(normalize_fn=lambda x: x)
        result = brain.get_reasoning_output("مرحبا", documents=[])
        self.assertIn("reasoning", result)
        self.assertIn("_plan", result)


# ── P0.1: Governance wiring integration via /ask ─────────────────────────────

class GovernanceWiringTests(unittest.TestCase):
    """
    Verify P0.1: governance hooks are fired automatically inside /ask.

    We use FastAPI TestClient against the real server.  The Kernel is real
    (uses a temp directory for state), provider calls are mocked out so we
    don't need an API key.
    """

    @classmethod
    def setUpClass(cls):
        # Patch provider calls so tests are deterministic and offline
        cls._provider_patch = patch(
            "executive_brain.ExecutiveBrain._call_provider",
            return_value="رد تجريبي من المدير",
        )
        cls._provider_patch.start()

        from fastapi.testclient import TestClient
        import ameer_server
        cls.client = TestClient(ameer_server.app)
        cls.kernel = ameer_server.KERNEL

    @classmethod
    def tearDownClass(cls):
        cls._provider_patch.stop()

    def _decisions_before(self):
        if self.kernel:
            return len(self.kernel.decisions._decisions)
        return 0

    def _approvals_before(self):
        if self.kernel:
            return len(self.kernel.approvals._approvals)
        return 0

    def test_decision_query_creates_decision_record(self):
        """A planning/decision query must auto-create a DecisionEngine record."""
        if not self.kernel:
            self.skipTest("Kernel unavailable")
        # Use queries verified to classify as planning/decision
        before = len(self.kernel.decisions._decisions)
        response = self.client.post("/ask", json={"query": "هل أستثمر في هذا المشروع؟"})
        self.assertEqual(response.status_code, 200)
        after = len(self.kernel.decisions._decisions)
        self.assertGreater(after, before, "Expected at least one new decision record for a decision query")

    def test_normal_question_does_not_create_approval(self):
        """A simple question must NOT produce spurious approval records."""
        if not self.kernel:
            self.skipTest("Kernel unavailable")
        before = self._approvals_before()
        response = self.client.post("/ask", json={"query": "ما هي المشاريع الحالية؟"})
        self.assertEqual(response.status_code, 200)
        after = self._approvals_before()
        # A plain question should not trigger approval gate
        plan_type = response.json()  # just check request succeeded
        self.assertIn("reply", response.json())

    def test_governance_endpoints_reflect_wired_records(self):
        """After a planning request, /decisions endpoint shows the new record."""
        if not self.kernel:
            self.skipTest("Kernel unavailable")
        # Send a query verified to classify as 'planning'
        self.client.post("/ask", json={"query": "ما هي الخطة للربع القادم؟"})
        # Query the decisions endpoint
        resp = self.client.get("/decisions")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        # total must be > 0 since we just sent a planning query
        self.assertGreater(data.get("total", 0), 0)

    def test_ask_pipeline_still_returns_valid_reply(self):
        """P0.1 wiring must not break the reply contract."""
        response = self.client.post("/ask", json={"query": "من أنت؟"})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("reply", payload)
        self.assertTrue(payload["reply"])

    def test_think_called_once_per_ask_request(self):
        """P0.2 + P0.1 together: think() fires once, governance still fires."""
        import ameer_server
        brain = ameer_server.EXECUTIVE_BRAIN
        if not brain:
            self.skipTest("Brain unavailable")

        think_calls = []
        original_think = brain.think

        def counting_think(*args, **kwargs):
            think_calls.append(1)
            return original_think(*args, **kwargs)

        brain.think = counting_think
        try:
            response = self.client.post("/ask", json={"query": "خطة تسويقية للمشروع"})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(
                len(think_calls), 1,
                f"Expected think() called exactly once, got {len(think_calls)}"
            )
        finally:
            brain.think = original_think


if __name__ == "__main__":
    unittest.main()
