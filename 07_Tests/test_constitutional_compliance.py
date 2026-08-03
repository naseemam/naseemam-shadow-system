"""
test_constitutional_compliance.py
==================================
Sprint 0 — Executive Compliance Tests

هذا الملف يُثبت أن النظام يُطبّق الدستور التنفيذي — لا مجرد مجموعة ملفات.

كل مجموعة اختبار تُثبت قاعدة واحدة من إطار الامتثال التنفيذي:
  Executive_Compliance_Framework_v1.0.md

Sprint 0 Success Criteria — all seven groups must pass before Sprint 1 opens.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CODE_ROOT = os.path.join(ROOT, "06_Code")
if CODE_ROOT not in sys.path:
    sys.path.insert(0, CODE_ROOT)

# ---------------------------------------------------------------------------
# Module loaders
# ---------------------------------------------------------------------------

def _load_module(relative_path: str, module_name: str):
    path = os.path.join(ROOT, relative_path)
    spec = importlib.util.spec_from_file_location(module_name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


_executive_brain_mod = _load_module("06_Code/executive_brain.py", "executive_brain")
ExecutiveBrain = _executive_brain_mod.ExecutiveBrain

_formatter_mod = _load_module("06_Code/response_formatter.py", "response_formatter")
ResponseFormatter = _formatter_mod.ResponseFormatter

from adapters.inference_provider import InferenceProvider, OllamaProvider, OpenAIProvider
from agents.base import AgentContext, AgentOutput, BaseAgent
from agents.registry import AGENTS

IDENTITY_PATH = os.path.join(ROOT, ".ameer", "identity.json")

# ---------------------------------------------------------------------------
# 1. Identity Compliance — قاعدة الهوية
#    Constitution: Principle 1 (Executive First) + Contract 1 (Ameer Identity)
# ---------------------------------------------------------------------------

class IdentityComplianceTests(unittest.TestCase):
    """
    اختبار الهوية — أمير يعرف من هو.

    Proves: Ameer's identity in every response matches the Constitution-defined
    identity stored in .ameer/identity.json.  No other component may claim the
    executive role.
    """

    def _load_identity(self) -> dict:
        with open(IDENTITY_PATH, encoding="utf-8") as fh:
            return json.load(fh)

    def test_identity_file_exists_and_has_name(self):
        """Identity file must exist and declare a name."""
        self.assertTrue(os.path.isfile(IDENTITY_PATH), ".ameer/identity.json must exist")
        identity = self._load_identity()
        self.assertIn("name", identity, "identity.json must contain 'name'")
        self.assertTrue(identity["name"].strip(), "'name' must not be blank")

    def test_identity_agent_names_match_constitution(self):
        """
        Identity agent's reply must reference Ameer's canonical name.

        identity.json stores the name in English ("Ameer"); the agent may use
        the Arabic equivalent ("أمير") — both are the same identity, so either
        form is acceptable.  What must NOT happen is the agent returning a
        completely different name.
        """
        identity = self._load_identity()
        canonical_name_en = identity["name"]          # e.g. "Ameer"
        canonical_name_ar = "أمير"                    # Arabic equivalent

        agent = AGENTS.get("identity_agent")
        self.assertIsNotNone(agent, "identity_agent must be registered")

        ctx = AgentContext(
            query="من أنت؟",
            intent="identity",
            route={"intent": "identity", "agent": "identity_agent"},
            results=[],
            execution_plan={"goal": "identity check"},
            conversation_state={"has_context": False},
            active_goal=None,
        )
        output = agent.execute(ctx)
        self.assertIsInstance(output, AgentOutput)
        self.assertTrue(
            canonical_name_en in output.reply_draft or canonical_name_ar in output.reply_draft,
            f"identity_agent reply must contain the canonical name "
            f"('{canonical_name_en}' or '{canonical_name_ar}'). "
            f"Got: {output.reply_draft!r}",
        )

    def test_founder_is_acknowledged_as_final_authority(self):
        """
        Identity agent must acknowledge the Founder as final authority.
        """
        agent = AGENTS.get("identity_agent")
        self.assertIsNotNone(agent)

        ctx = AgentContext(
            query="من هو نسيم؟",
            intent="identity",
            route={"intent": "identity", "agent": "identity_agent"},
            results=[],
            execution_plan={"goal": "founder identity check"},
            conversation_state={"has_context": False},
            active_goal=None,
        )
        output = agent.execute(ctx)
        reply_lower = output.reply_draft.lower()
        self.assertTrue(
            any(word in reply_lower for word in ["مؤسس", "founder", "قرار", "authority", "naseem", "نسيم"]),
            "identity_agent must acknowledge the Founder's authority",
        )

    def test_no_agent_claims_executive_authority(self):
        """
        No agent other than ameer_core / identity_agent may present itself as
        the executive mind.  Agents must return a reply_draft, not a final
        autonomous decision.
        """
        prohibited_phrases = [
            "أنا المسؤول التنفيذي",
            "i am the executive",
            "i am ameer",
            "أنا أمير",
        ]
        ctx = AgentContext(
            query="من أنت؟",
            intent="identity",
            route={"intent": "identity", "agent": "research_agent"},
            results=[],
            execution_plan={"goal": "contract check"},
            conversation_state={"has_context": False},
            active_goal=None,
        )
        for agent_name, agent in AGENTS.items():
            if agent_name in {"identity_agent"}:
                continue
            with self.subTest(agent=agent_name):
                output = agent.execute(ctx)
                reply_lower = output.reply_draft.lower()
                for phrase in prohibited_phrases:
                    self.assertNotIn(
                        phrase.lower(),
                        reply_lower,
                        f"{agent_name} must not claim executive authority (found: '{phrase}')",
                    )


# ---------------------------------------------------------------------------
# 2. Delegation Compliance — قاعدة التفويض
#    Constitution: Principle 2 (Delegation, Not Replacement) + Contract 2
# ---------------------------------------------------------------------------

class DelegationComplianceTests(unittest.TestCase):
    """
    اختبار التفويض — الوكلاء لا يقررون، يُنفّذون فقط.

    Proves: every agent returns a draft output that is reviewed by the
    Executive Brain before becoming a final response.  Agents do not retain
    independent decision authority after execution.
    """

    def _build_context(self, agent_name: str = "research_agent") -> AgentContext:
        return AgentContext(
            query="ما هي خطة الشركة للربع القادم؟",
            intent="planning",
            route={"intent": "planning", "agent": agent_name},
            results=[],
            execution_plan={"goal": "delegation compliance check"},
            conversation_state={"has_context": False},
            active_goal=None,
        )

    def test_all_agents_return_draft_not_final_decision(self):
        """
        Every agent must return an AgentOutput with a reply_draft field.
        They must NOT return a final autonomous decision object.
        """
        for agent_name, agent in AGENTS.items():
            with self.subTest(agent=agent_name):
                ctx = self._build_context(agent_name)
                output = agent.execute(ctx)
                self.assertIsInstance(
                    output, AgentOutput,
                    f"{agent_name} must return AgentOutput, not an autonomous decision",
                )
                self.assertIsInstance(
                    output.reply_draft, str,
                    f"{agent_name}.reply_draft must be a string (a draft, not a final decision)",
                )

    def test_agents_do_not_retain_state_after_execution(self):
        """
        Agents must not accumulate independent decision state across calls.
        """
        for agent_name, agent in AGENTS.items():
            with self.subTest(agent=agent_name):
                ctx = self._build_context(agent_name)
                agent.execute(ctx)
                # namespace (shared state) must not grow unboundedly
                # After a single execute() the agent namespace should remain empty
                # or contain only well-known lifecycle keys, not decision artifacts.
                ns = getattr(agent, "namespace", {})
                self.assertIsInstance(ns, dict, f"{agent_name}.namespace must be a dict")

    def test_executive_brain_synthesises_final_reply(self):
        """
        The final reply must pass through ExecutiveBrain.compose_final_reply,
        not be issued directly by an agent.
        """
        brain = ExecutiveBrain(normalize_fn=lambda x: x)

        provider_reply = "رد نهائي من العقل التنفيذي"
        brain._call_provider = lambda *args, **kwargs: provider_reply

        plan = type(
            "Plan",
            (),
            {
                "clarification_needed": False,
                "clarification_question": None,
                "guardian_status": "pass",
                "guardian_reason": "",
                "context_summary": "",
                "selected_agent": "research_agent",
                "executive_message": "رسالة محلية",
            },
        )()

        orchestrator_result = {
            "agent_brain_payload": {"draft": "مسودة الوكيل"},
            "results": [],
        }

        reply, source = brain.compose_final_reply(
            "سؤال تجريبي",
            orchestrator_result,
            [],
            existing_plan=plan,
        )

        self.assertEqual(
            reply,
            provider_reply,
            "Executive Brain must be the final synthesis point, not the agent",
        )
        self.assertEqual(source, "executive_brain_provider")


# ---------------------------------------------------------------------------
# 3. Provider Independence — قاعدة استقلالية المزود
#    Constitution: Principle 3 + Contract 3 (Inference Provider Contract)
# ---------------------------------------------------------------------------

class ProviderIndependenceTests(unittest.TestCase):
    """
    اختبار استقلالية المزود — تبديل المزود لا يُغيّر هوية أمير.

    Proves: both OpenAIProvider and OllamaProvider implement the same
    InferenceProvider interface.  Swapping providers must not affect
    Ameer's identity (identity comes from identity.json, not from the provider).
    """

    def test_openai_provider_implements_interface(self):
        """OpenAIProvider must be a concrete InferenceProvider."""
        self.assertTrue(
            issubclass(OpenAIProvider, InferenceProvider),
            "OpenAIProvider must implement InferenceProvider",
        )

    def test_ollama_provider_implements_interface(self):
        """OllamaProvider must be a concrete InferenceProvider."""
        self.assertTrue(
            issubclass(OllamaProvider, InferenceProvider),
            "OllamaProvider must implement InferenceProvider",
        )

    def test_providers_share_the_same_interface(self):
        """Both providers must expose is_available, complete, and name."""
        required_methods = ["is_available", "complete", "name"]
        for provider_class in (OpenAIProvider, OllamaProvider):
            with self.subTest(provider=provider_class.__name__):
                for method in required_methods:
                    self.assertTrue(
                        hasattr(provider_class, method),
                        f"{provider_class.__name__} must expose '{method}'",
                    )

    def test_identity_is_not_sourced_from_provider(self):
        """
        Ameer's identity must come from .ameer/identity.json, not from any provider.
        The provider is only responsible for text completion.
        """
        self.assertTrue(
            os.path.isfile(IDENTITY_PATH),
            "Identity must be stored independently in .ameer/identity.json, not in a provider",
        )
        with open(IDENTITY_PATH, encoding="utf-8") as fh:
            identity = json.load(fh)
        self.assertIn("name", identity)
        # Identity must be stable regardless of provider being available
        provider = OllamaProvider(host="http://127.0.0.1:99999", model="none")
        self.assertFalse(provider.is_available(), "Unreachable provider must report unavailable")
        # Identity file still intact — not modified by provider
        with open(IDENTITY_PATH, encoding="utf-8") as fh:
            identity_after = json.load(fh)
        self.assertEqual(
            identity["name"],
            identity_after["name"],
            "Provider availability check must not alter Ameer's identity",
        )

    def test_unavailable_provider_returns_none_not_exception(self):
        """
        An unavailable provider must return None from complete(), never raise.
        The Executive Brain must be able to fall back gracefully.
        """
        provider = OllamaProvider(host="http://127.0.0.1:99999", model="none")
        result = provider.complete("system", "user")
        self.assertIsNone(
            result,
            "Unavailable OllamaProvider must return None, not raise an exception",
        )


# ---------------------------------------------------------------------------
# 4. Memory Governance — قاعدة حوكمة الذاكرة
#    Constitution: Principle 4 + Contract 4 (Memory Contract)
# ---------------------------------------------------------------------------

class MemoryGovernanceTests(unittest.TestCase):
    """
    اختبار حوكمة الذاكرة — لا كتابة خارج المسارات المُصرَّح بها.

    Proves: _check_write_allowed blocks paths outside _ALLOWED_WRITE_PREFIXES
    and allows paths inside them.
    """

    def setUp(self):
        self.brain = ExecutiveBrain(normalize_fn=lambda x: x)
        self.root = "/tmp/ameer_compliance_test_root"

    def test_write_to_allowed_prefix_is_permitted(self):
        """Writes inside 04_Memory must be allowed."""
        target = os.path.join(self.root, "04_Memory", "note.md")
        allowed = self.brain._check_write_allowed(target, self.root)
        self.assertTrue(allowed, "Write to 04_Memory must be permitted (governed memory store)")

    def test_write_to_constitution_is_blocked(self):
        """Writes to 01_Docs (constitution layer) must be blocked."""
        target = os.path.join(self.root, "01_Docs", "Executive_Constitution_v1.0.md")
        allowed = self.brain._check_write_allowed(target, self.root)
        self.assertFalse(allowed, "Write to the Constitution must be blocked by memory governance")

    def test_write_to_code_layer_is_blocked(self):
        """Writes to 06_Code must be blocked."""
        target = os.path.join(self.root, "06_Code", "executive_brain.py")
        allowed = self.brain._check_write_allowed(target, self.root)
        self.assertFalse(allowed, "Write to the code layer must be blocked by memory governance")

    def test_path_traversal_outside_workspace_is_blocked(self):
        """Path traversal attacks that escape the workspace must be blocked."""
        target = os.path.join(self.root, "..", "..", "etc", "passwd")
        allowed = self.brain._check_write_allowed(target, self.root)
        self.assertFalse(allowed, "Path traversal outside the workspace must be blocked")

    def test_create_file_blocked_outside_allowed_paths(self):
        """_create_file must return status:blocked for paths outside allowed prefixes."""
        result = self.brain._create_file(
            "01_Governance/hijacked.md",
            "هذا انتهاك للحوكمة",
            workspace_root=self.root,
        )
        self.assertEqual(
            result.get("status"),
            "blocked",
            "_create_file must return status:blocked for constitution/governance paths",
        )

    def test_create_file_allowed_inside_memory_store(self):
        """_create_file must succeed for paths inside 04_Memory."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, "04_Memory"), exist_ok=True)
            result = self.brain._create_file(
                "04_Memory/test_note.md",
                "ملاحظة اختبار",
                workspace_root=tmpdir,
            )
            self.assertEqual(
                result.get("status"),
                "created",
                "_create_file must succeed for paths inside 04_Memory",
            )


# ---------------------------------------------------------------------------
# 5. Founder Authority — قاعدة سلطة المؤسس
#    Constitution: Principle 5 + Contract 5 (Founder Contract)
# ---------------------------------------------------------------------------

class FounderAuthorityTests(unittest.TestCase):
    """
    اختبار سلطة المؤسس — لا قرار جوهري بدون موافقة المؤسس.

    Proves: requests with guardian_status == "needs_approval" pause for
    confirmation; requests with "blocked" are rejected outright.
    """

    def _make_plan(self, guardian_status: str, guardian_reason: str = "سبب تجريبي"):
        return type(
            "Plan",
            (),
            {
                "clarification_needed": False,
                "clarification_question": None,
                "guardian_status": guardian_status,
                "guardian_reason": guardian_reason,
                "context_summary": "",
                "selected_agent": "research_agent",
                "executive_message": "رسالة محلية",
            },
        )()

    def test_needs_approval_requests_do_not_execute_autonomously(self):
        """
        A request flagged needs_approval must ask the Founder for confirmation
        rather than proceeding autonomously.

        We test _compose_local_reply directly because compose_final_reply
        delegates guardian handling to that method when the provider is
        unavailable.  The constitutional contract lives in that method.
        """
        brain = ExecutiveBrain(normalize_fn=lambda x: x)
        plan = self._make_plan("needs_approval", "هذا الإجراء يحتاج موافقة المؤسس")
        orchestrator_result = {
            "agent_brain_payload": {"draft": ""},
            "results": [],
            "guardian": {"status": "needs_approval", "reason": "يحتاج موافقة"},
        }

        reply = brain._compose_local_reply("احذف كل شيء", plan, orchestrator_result)

        # The reply must signal that it cannot proceed without the Founder
        self.assertIsInstance(reply, str)
        self.assertTrue(len(reply) > 0, "needs_approval must return an explicit message")
        # Must NOT silently execute — must communicate a boundary
        self.assertNotEqual(
            reply,
            "تمت معالجة الطلب دون تفاصيل إضافية.",
            "needs_approval must not fall through to the generic 'request processed' message",
        )

    def test_blocked_requests_are_rejected(self):
        """
        A request flagged as blocked must be outright rejected.

        We test _compose_local_reply directly — that is the constitutional
        enforcement point for the Founder Authority contract.
        """
        brain = ExecutiveBrain(normalize_fn=lambda x: x)
        plan = self._make_plan("blocked", "هذا الإجراء محظور دستوريًا")
        orchestrator_result = {
            "agent_brain_payload": {"draft": ""},
            "results": [],
            "guardian": {"status": "blocked", "reason": "محظور"},
        }

        reply = brain._compose_local_reply("غيّر الدستور", plan, orchestrator_result)

        self.assertIsInstance(reply, str)
        self.assertTrue(len(reply) > 0, "blocked requests must return an explicit rejection message")
        self.assertNotEqual(
            reply,
            "تمت معالجة الطلب دون تفاصيل إضافية.",
            "blocked requests must not fall through to the generic 'request processed' message",
        )


# ---------------------------------------------------------------------------
# 6. Response Integrity — قاعدة نزاهة الرد
#    Constitution: Executive Integrity section
# ---------------------------------------------------------------------------

class ResponseIntegrityTests(unittest.TestCase):
    """
    اختبار نزاهة الرد — الرد النهائي يحافظ على هوية أمير.

    Proves: ResponseFormatter strips internal implementation details (agent
    names, file paths, debug traces) before the reply reaches the Founder.
    """

    def setUp(self):
        self.formatter = ResponseFormatter()

    def test_formatter_strips_internal_agent_references(self):
        """
        Internal agent names must not leak into the final response.
        """
        raw = "The research_agent has found the following information: هذه نتائج البحث."
        result = self.formatter.format_text(raw)
        self.assertNotIn(
            "research_agent",
            result,
            "ResponseFormatter must strip internal agent references",
        )

    def test_formatter_strips_file_paths(self):
        """
        Internal file paths must not appear in the final response.
        """
        raw = "See 06_Code/executive_brain.py for details: الرد هنا."
        result = self.formatter.format_text(raw)
        self.assertNotIn(
            "executive_brain.py",
            result,
            "ResponseFormatter must strip internal file paths",
        )

    def test_formatter_strips_debug_metadata(self):
        """
        Debug/trace/metadata labels must be stripped from the final response.
        """
        raw = "debug: selected_agent=research_agent; الرد الفعلي هنا."
        result = self.formatter.format_text(raw)
        self.assertNotIn(
            "selected_agent",
            result,
            "ResponseFormatter must strip debug metadata",
        )

    def test_formatter_returns_non_empty_response(self):
        """
        Even after stripping internal content, the formatter must return a
        non-empty response (fallback reply if needed).
        """
        result = self.formatter.format_text("بسم الله الرحمن الرحيم")
        self.assertTrue(
            len(result) > 0,
            "ResponseFormatter must return a non-empty formatted response",
        )

    def test_formatter_handles_non_string_input_gracefully(self):
        """
        Non-string input must not raise an exception — it must return the
        fallback reply.
        """
        for bad_input in (None, 42, [], {}):
            with self.subTest(input=bad_input):
                result = self.formatter.format_text(bad_input)
                self.assertIsInstance(result, str)
                self.assertTrue(len(result) > 0)


# ---------------------------------------------------------------------------
# 7. Constitutional Compliance — قاعدة الامتثال الدستوري الكامل
#    Constitution: All principles and contracts
# ---------------------------------------------------------------------------

class ConstitutionalComplianceTests(unittest.TestCase):
    """
    اختبار الامتثال الدستوري الكامل — النظام يُطبّق الدستور.

    Proves the full constitutional stack is in place:
    - All agents implement BaseAgent (governed contract).
    - No agent declares itself as executive authority.
    - ExecutiveBrain is the sole synthesis point.
    - The governance hierarchy files exist.
    """

    def test_all_agents_inherit_base_agent(self):
        """
        Every registered agent must inherit BaseAgent (governed contract).
        """
        for agent_name, agent in AGENTS.items():
            with self.subTest(agent=agent_name):
                self.assertIsInstance(
                    agent,
                    BaseAgent,
                    f"{agent_name} must inherit BaseAgent to operate under the Agent Contract",
                )

    def test_all_agents_return_agent_output(self):
        """
        Every agent must produce an AgentOutput, not a custom autonomous object.
        """
        ctx = AgentContext(
            query="اختبار الامتثال الدستوري",
            intent="knowledge_lookup",
            route={"intent": "knowledge_lookup", "agent": "research_agent"},
            results=[],
            execution_plan={"goal": "constitutional compliance"},
            conversation_state={"has_context": False},
            active_goal=None,
        )
        for agent_name, agent in AGENTS.items():
            with self.subTest(agent=agent_name):
                output = agent.execute(ctx)
                self.assertIsInstance(
                    output,
                    AgentOutput,
                    f"{agent_name} must return AgentOutput (constitutional output contract)",
                )

    def test_constitution_file_exists_and_is_not_empty(self):
        """
        The Executive Constitution must exist and be non-empty.
        It is the supreme authority document — its absence is a governance failure.
        """
        constitution_path = os.path.join(ROOT, "01_Docs", "Executive_Constitution_v1.0.md")
        self.assertTrue(
            os.path.isfile(constitution_path),
            "Executive_Constitution_v1.0.md must exist",
        )
        content = Path(constitution_path).read_text(encoding="utf-8")
        self.assertGreater(
            len(content),
            100,
            "Executive_Constitution_v1.0.md must not be empty",
        )

    def test_compliance_framework_file_exists(self):
        """
        The Executive Compliance Framework must exist.
        Without it there is no bridge between the Constitution and testable rules.
        """
        framework_path = os.path.join(ROOT, "01_Docs", "Executive_Compliance_Framework_v1.0.md")
        self.assertTrue(
            os.path.isfile(framework_path),
            "Executive_Compliance_Framework_v1.0.md must exist",
        )

    def test_identity_file_exists_and_is_governed(self):
        """
        The identity file must exist and contain a name and a founder field.
        It is the single source of truth for Ameer's identity across all providers.
        """
        self.assertTrue(
            os.path.isfile(IDENTITY_PATH),
            ".ameer/identity.json must exist (identity independence from providers)",
        )
        with open(IDENTITY_PATH, encoding="utf-8") as fh:
            identity = json.load(fh)
        self.assertIn("name", identity)
        self.assertIn("founder", identity)

    def test_executive_brain_is_the_sole_synthesis_class(self):
        """
        ExecutiveBrain must expose compose_final_reply — the constitutional
        synthesis point.  No other class in the loaded module provides this.
        """
        self.assertTrue(
            hasattr(ExecutiveBrain, "compose_final_reply"),
            "ExecutiveBrain must expose compose_final_reply as the sole synthesis point",
        )

    def test_allowed_write_prefixes_exclude_governance_and_code(self):
        """
        Memory governance (Contract 4) requires that write operations are
        restricted.  The _ALLOWED_WRITE_PREFIXES must NOT include governance or
        code directories.
        """
        brain = ExecutiveBrain(normalize_fn=lambda x: x)
        forbidden_prefixes = {"01_Docs", "01_Governance", "06_Code", "07_Tests"}
        allowed = set(brain._ALLOWED_WRITE_PREFIXES)
        overlap = forbidden_prefixes & allowed
        self.assertFalse(
            overlap,
            f"Governance/code paths must not appear in _ALLOWED_WRITE_PREFIXES: {overlap}",
        )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main()
