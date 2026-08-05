"""
executive_brain.py
==================
Ameer's Executive Brain — the top-most thinking layer.

Hierarchy:
  Executive Brain
    → Intent Classification (Perception)
    → Context Linking (cross-project awareness)
    → Planning (direct answer vs multi-step plan)
    → Agent Selection (which specialist to use)
    → Guardian Check (safety & approval gate)
    → Reflection (memory update signal)

This module wraps the reasoning_orchestrator and adds structured
decision-making on top. It returns a rich ExecutivePlan that the
API layer renders to the founder.
"""

from __future__ import annotations

import os
import re
import json
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

try:
    from adapters.inference_provider import InferenceProvider, OpenAIProvider, OllamaProvider
except Exception:  # pragma: no cover - fallback when run without package context
    InferenceProvider = None  # type: ignore[assignment,misc]
    OpenAIProvider = None  # type: ignore[assignment]
    OllamaProvider = None  # type: ignore[assignment]

try:
    from openai import OpenAI
except Exception:  # pragma: no cover - optional dependency
    OpenAI = None


# ─── Enumerations ─────────────────────────────────────────────────────────────

REQUEST_TYPES = {
    "question": ["ما", "من", "كيف", "متى", "أين", "هل", "what", "who", "how", "when", "where", "وضع", "حال", "status"],
    "analysis": ["لماذا", "سبب", "analyze", "why", "explain", "تحليل", "تأخر", "فشل", "نجح", "نتيجة"],
    "planning": ["خطة", "خطط", "كيف أطلق", "كيف أبدأ", "كيف أطلق", "كيف أبدأ", "plan", "roadmap", "خارطة", "أطلق", "ابدأ", "انطلق", "خطوات", "مراحل", "launch", "start", "go live"],
    "decision": ["هل أستثمر", "هل أوافق", "قرر", "decide", "should i", "هل يجب", "أستثمر", "أوافق", "أختار", "أقبل", "أرفض", "قرار"],
    "execution": ["أنشئ", "اكتب", "نفذ", "create", "write", "build", "generate", "أضف", "احذف", "عدّل", "أرسل", "شغّل", "file", "ملف", "new"],
    "memory": ["تذكر", "احفظ", "remember", "save", "لا تنسَ", "سجّل", "أضف للذاكرة"],
    "creative": ["اقترح", "اختر اسم", "فكرة", "suggest", "brainstorm", "ideas", "اسم", "أفكار", "ابتكر"],
}

AGENT_CATALOG = {
    "ameer_core": {
        "description": "أمير كور — العقل التنفيذي الأساسي وصاحب الرد النهائي",
        "keywords": ["أمير", "امير", "من أنت", "من انت", "عرف بنفسك", "ماذا تستطيع", "هل تفهمني"],
    },
    "greeting_agent": {
        "description": "وكيل الترحيب — بدء المحادثة بنبرة واضحة وطبيعية",
        "keywords": ["مرحبا", "أهلا", "اهلا", "سلام", "hello", "hi", "hey"],
    },
    "project_manager": {
        "description": "مدير المشاريع — المهام والجداول والمواعيد",
        "keywords": ["مشروع", "مهمة", "موعد", "deadline", "task", "project", "milestone"],
    },
    "investment_agent": {
        "description": "وكيل الاستثمار — تحليل الفرص المالية",
        "keywords": ["استثمار", "investment", "عائد", "return", "portfolio", "risk"],
    },
    "finance_agent": {
        "description": "وكيل المالية — الميزانية والتدفق النقدي",
        "keywords": ["ميزانية", "مال", "تدفق", "budget", "cashflow", "finance", "مصاريف"],
    },
    "legal_agent": {
        "description": "الوكيل القانوني — العقود والامتثال",
        "keywords": ["عقد", "قانون", "contract", "legal", "compliance", "امتثال"],
    },
    "web_agent": {
        "description": "وكيل المواقع — الحضور الرقمي",
        "keywords": ["موقع", "website", "domain", "hosting", "seo", "دومين"],
    },
    "code_agent": {
        "description": "وكيل البرمجة — الكود والتقنية",
        "keywords": ["كود", "برمجة", "code", "bug", "api", "git", "deploy", "database"],
    },
    "design_agent": {
        "description": "وكيل التصميم — UI/UX والجماليات",
        "keywords": ["تصميم", "design", "logo", "ui", "ux", "color", "font", "شعار"],
    },
    "company_agent": {
        "description": "وكيل إدارة الشركة — الفريق والعمليات",
        "keywords": ["شركة", "فريق", "توظيف", "company", "team", "hire", "operations"],
    },
    "personal_agent": {
        "description": "الوكيل الشخصي — الصحة والعادات والأهداف",
        "keywords": ["صحة", "عادة", "هدف", "health", "habit", "goal", "personal", "شخصي"],
    },
    "research_agent": {
        "description": "وكيل البحث — جمع المعلومات والتحليل",
        "keywords": ["ابحث", "بحث", "research", "find", "market", "سوق", "منافس"],
    },
    "memory_agent": {
        "description": "وكيل الذاكرة — الحفظ والاسترجاع",
        "keywords": ["ذاكرة", "تذكر", "احفظ", "memory", "remember", "recall"],
    },
}

AUTONOMY_LEVELS = ["inform", "suggest", "act_with_approval", "act_autonomously"]


# ─── Data Classes ─────────────────────────────────────────────────────────────

@dataclass
class PerceptionResult:
    request_type: str
    confidence: float
    ambiguous: bool
    clarification_needed: bool
    clarification_question: Optional[str] = None


@dataclass
class ContextLink:
    project: str
    relevance: str
    constraint: Optional[str] = None


@dataclass
class AgentSelection:
    primary_agent: str
    supporting_agents: List[str]
    reasoning: str


@dataclass
class ExecutivePlan:
    """Full decision output from the Executive Brain."""

    # Perception
    request_type: str
    ambiguous: bool
    clarification_needed: bool
    clarification_question: Optional[str]

    # Context
    context_links: List[ContextLink]
    context_summary: str

    # Planning
    plan_type: str                   # "direct" | "multi_step"
    steps: List[str]

    # Agent
    selected_agent: str
    supporting_agents: List[str]
    agent_reasoning: str

    # Guardian
    guardian_status: str             # "pass" | "needs_approval" | "blocked"
    guardian_reason: str
    autonomy_level: str

    # Reflection
    should_remember: bool
    memory_note: Optional[str]

    # Final message to founder
    executive_message: str


# ─── Executive Brain ──────────────────────────────────────────────────────────

class ExecutiveBrain:
    """
    Ameer's Executive Brain.

    Takes a raw query and the current document context, and produces
    a structured ExecutivePlan that guides the orchestrator + response.
    """

    def __init__(self, normalize_fn=None):
        self._normalize = normalize_fn or (lambda x: x)
        self._openai_client = None
        self._single_brain_mode = os.getenv("AMEER_SINGLE_BRAIN", "1").lower() in {"1", "true", "yes", "on"}
        self._model_name = os.getenv("AMEER_MODEL", "gpt-4o-mini")
        self._ollama_host = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
        self._ollama_model = os.getenv("OLLAMA_MODEL", "smollm:135m")

        # Build ordered provider chain via the formal abstraction when available.
        self._providers: List[object] = []
        if OpenAIProvider is not None:
            # Primary: explicit OPENAI_API_KEY (standard OpenAI or any compatible API).
            api_key = os.getenv("OPENAI_API_KEY")
            base_url = os.getenv("OPENAI_BASE_URL") or None
            if not api_key:
                # Fallback: use the GitHub Copilot token with the Copilot chat endpoint,
                # which is fully OpenAI-API-compatible (no extra headers required).
                api_key = os.getenv("GITHUB_COPILOT_API_TOKEN") or os.getenv("GITHUB_TOKEN")
                if api_key and not base_url:
                    base_url = "https://api.githubcopilot.com"
            if api_key:
                self._providers.append(
                    OpenAIProvider(api_key=api_key, model=self._model_name, base_url=base_url)
                )
        if OllamaProvider is not None and os.getenv("OLLAMA_ENABLED", "1").lower() in {"1", "true", "yes", "on"}:
            self._providers.append(OllamaProvider(host=self._ollama_host, model=self._ollama_model))

        # Legacy direct openai client kept for backwards compat with tests that
        # patch _openai_client directly.
        if OpenAI is not None:
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                try:
                    self._openai_client = OpenAI(api_key=api_key)
                except Exception:
                    self._openai_client = None

    def _execution_step(self, name: str, status: str = "pending", detail: str = "") -> dict:
        return {
            "name": name,
            "status": status,
            "detail": detail,
        }

    def _update_step(self, steps: List[dict], name: str, status: str, detail: str = "") -> None:
        for step in steps:
            if step.get("name") == name:
                step["status"] = status
                if detail:
                    step["detail"] = detail
                return
        steps.append(self._execution_step(name=name, status=status, detail=detail))

    def _build_provider_prompt(
        self,
        prompt: str,
        plan: ExecutivePlan | None = None,
        conversation_context: str = "",
        founder_context: str = "",
        workspace_summary: str = "",
        pending_approvals: Optional[List[dict]] = None,
        active_projects: Optional[List[str]] = None,
        running_tasks: Optional[List[dict]] = None,
        is_first_turn: bool = False,
    ) -> tuple[str, str]:
        # ── Executive Identity ──────────────────────────────────────────────
        system_prompt = (
            "أنت أمير — شريك نسيم التنفيذي. تعرفها، تعرف مشاريعها، تتابع أولوياتها.\n\n"
            "هويتك:\n"
            "- لستَ مساعدًا، ولستَ نظام دردشة. أنت الشريك التنفيذي الذي يفكر ويخطط ويقرر ويتابع.\n"
            "- نسيم هي المؤسسة وصاحبة القرار النهائي. العلاقة بينكما شراكة حقيقية، لا خدمة.\n"
            "- أنت تعرف ما يجري في المشاريع وما لم يُغلق وما يحتاج قرارًا.\n\n"
            "طريقة الحوار:\n"
            "- تحدث مثل شريك تنفيذي يكمل جملته الأخيرة ويعرف من أين توقف.\n"
            "- لا تبدأ بالتحيات ولا بالتأكيد المفرط ولا بالإشارة إلى أنك 'ستساعد'.\n"
            "- كن مباشرًا: قل رأيك، حدد المخاطر عند رؤيتها، اقترح الخطوة التالية دون انتظار السؤال.\n"
            "- إذا كان الأمر بسيطًا أجب مختصرًا. إذا كان معقدًا افصّل بقدر ما يلزم.\n"
            "- اسأل سؤالًا واحدًا فقط عند الغموض — لا قائمة أسئلة.\n"
            "- لا تكشف أسماء الوكلاء أو المكونات الداخلية.\n"
            "- لا تبدأ بـ 'سأستخدم...' أو 'سأعمل على...' أو أي تفاصيل تقنية داخلية.\n"
            "- اللغة العربية الطبيعية دائمًا.\n\n"
            "You are Ameer, Naseem's executive partner. Always reply in natural Arabic. "
            "Think like a long-term partner who already knows the context. "
            "End every reply with the most logical next step or one direct question. "
            "Never mention internal architecture, agents, or reasoning chains."
        )

        # ── Inject live context blocks ──────────────────────────────────────
        context_parts: List[str] = []

        if founder_context:
            context_parts.append(founder_context)

        if workspace_summary:
            context_parts.append(workspace_summary)

        # ── Active Projects ─────────────────────────────────────────────────
        if active_projects:
            projects_block = "[ المشاريع النشطة: " + " | ".join(active_projects[:6]) + " ]"
            context_parts.append(projects_block)

        # ── Pending Approvals ───────────────────────────────────────────────
        if pending_approvals:
            items = "; ".join(
                str(a.get("summary") or a.get("title") or a.get("id") or "قرار معلّق")
                for a in pending_approvals[:3]
            )
            approvals_block = f"[ قرارات تنتظر موافقتكِ ({len(pending_approvals)}): {items} ]"
            context_parts.append(approvals_block)

        # ── Running Tasks ───────────────────────────────────────────────────
        if running_tasks:
            task_names = "; ".join(
                str(t.get("title") or t.get("name") or t.get("id") or "مهمة جارية")
                for t in running_tasks[:3]
            )
            tasks_block = f"[ مهام قيد التنفيذ ({len(running_tasks)}): {task_names} ]"
            context_parts.append(tasks_block)

        context_summary = (plan.context_summary if plan else "").strip()
        if context_summary and context_summary != "لم يُكتشف ارتباط مباشر بمشاريع أخرى.":
            context_parts.append(f"[ ارتباطات المشروع: {context_summary} ]")

        if conversation_context:
            context_parts.append(conversation_context)

        # ── Build user prompt ───────────────────────────────────────────────
        prefix = "\n\n".join(context_parts)

        # First-turn post-startup: ask Ameer to open with a proactive executive briefing
        if is_first_turn:
            startup_instruction = (
                "هذه أول رسالة بعد تشغيل النظام.\n"
                "إذا كانت هناك تغييرات مهمة أو مهام معلّقة أو قرارات تنتظر، "
                "ابدأ بملخص تنفيذي موجز يعكس الوضع الحالي قبل الإجابة على الطلب.\n"
                "لا تنتظر أن تُسأل — اعرض الملخص بشكل طبيعي كما يفعل شريك تنفيذي يستأنف العمل."
            )
            if prefix:
                user_prompt = f"{prefix}\n\n{startup_instruction}\n\n{prompt}"
            else:
                user_prompt = f"{startup_instruction}\n\n{prompt}"
        elif prefix:
            user_prompt = f"{prefix}\n\n{prompt}"
        else:
            user_prompt = prompt
        return system_prompt, user_prompt

    def _sanitize_provider_reply(self, text: str) -> str:
        cleaned = (text or "").strip()
        if not cleaned:
            return ""

        cleaned = re.sub(r"```(?:\w+)?", "", cleaned)
        cleaned = cleaned.replace("\u200f", "").strip()

        instruction_like_patterns = [
            r"\bthe final answer should\b",
            r"\bthe answer should\b",
            r"\buser request\s*:\b",
            r"\bcontext\s*:\b",
            r"\bthe user is asking for\b",
            r"\binternal prompt\b",
            r"\bplanning, reasoning\b",
            r"\bplanning and reasoning\b",
            r"\bto help the user understand what they need to do next\b",
            r"\bthis way, the user can\b",
            r"\buser requests\b",
            r"\bcontext:\b",
            r"\breply with only the final assistant answer\b",
            r"\basked to reply\b",
            r"\bthe user is asked to\b",
            r"\bsingle answer in arabic\b",
            r"\breply in arabic\b",
            r"\bdifficult for a human\b",
        ]
        if any(re.search(pattern, cleaned, re.IGNORECASE) for pattern in instruction_like_patterns):
            return ""

        prefix_patterns = [
            r"^the correct answer is\s*",
            r"^the answer is\s*",
            r"^final answer\s*[:\-]\s*",
            r"^assistant answer\s*[:\-]\s*",
            r"^answer\s*[:\-]\s*",
            r"^الجواب\s*[:\-]\s*",
            r"^الإجابة الصحيحة هي\s*",
            r"^الإجابة النهائية\s*[:\-]\s*",
            r"^الرد النهائي\s*[:\-]\s*",
        ]
        for pattern in prefix_patterns:
            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)

        cleaned = re.sub(r"^[\s\-\*]+", "", cleaned)
        cleaned = re.sub(r"^[\"'“”]+", "", cleaned)
        cleaned = re.sub(r"[\"'“”]+$", "", cleaned)

        lines = []
        for raw_line in cleaned.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if re.match(r"^(system prompt|planning prompt|agent|routing|reasoning|chain of thought|execution plan|metadata|internal prompt|internal reasoning)\s*[:\-]", line, re.IGNORECASE):
                continue
            if re.match(r"^(الوكيل|التخطيط|التوجيه|التفكير|سلسلة التفكير|خطة التنفيذ|البيانات الداخلية|المنطق الداخلي)\s*[:\-]", line, re.IGNORECASE):
                continue
            if re.match(r"^(user request|context|prompt|instruction)\s*[:\-]", line, re.IGNORECASE):
                continue
            if re.match(r"^(the answer is|the correct answer is|final answer|assistant answer|answer)\s*", line, re.IGNORECASE):
                continue
            if re.search(r"\bthe user is asking for\b", line, re.IGNORECASE):
                continue
            lines.append(line)

        if lines:
            cleaned = " ".join(lines).strip()

        return cleaned

    def _extract_response_data(self, orchestrator_result: dict) -> dict:
        if not isinstance(orchestrator_result, dict):
            return {}
        for key in ("agent_brain_payload", "agent_result"):
            candidate = orchestrator_result.get(key)
            if isinstance(candidate, dict):
                response_data = candidate.get("response_data", {})
                if isinstance(response_data, dict) and response_data:
                    return response_data
        return {}

    def _compose_trusted_core_reply(self, orchestrator_result: dict) -> str:
        response_data = self._extract_response_data(orchestrator_result)
        intent = str(response_data.get("intent", "")).strip().lower()
        facts = response_data.get("facts", {})
        if not isinstance(facts, dict):
            facts = {}

        if intent == "identity":
            subject = str(facts.get("subject", "")).strip().lower()
            if subject == "founder":
                return "نسيم هي المؤسسة وصاحبة القرار، وأنا أعمل تحت سلطتها مباشرة."
            return "أنا أمير، شريكك التنفيذي. أفكر معك، أخطط، أتابع، وأقدم الرد النهائي باسمي."

        if intent == "greeting":
            mode = str(facts.get("mode", "")).strip().lower()
            if mode == "name_call":
                return "أنا هنا. من أين نبدأ؟"
            return "نبدأ من أعلى نقطة أثرًا — ما الذي يحتاج قرارًا أو تقدمًا الآن؟"

        return ""

    def _call_provider(
        self,
        prompt: str,
        plan: ExecutivePlan | None = None,
        conversation_context: str = "",
        founder_context: str = "",
        workspace_summary: str = "",
        pending_approvals: Optional[List[dict]] = None,
        active_projects: Optional[List[str]] = None,
        running_tasks: Optional[List[dict]] = None,
        is_first_turn: bool = False,
    ) -> Optional[str]:
        system_prompt, user_prompt = self._build_provider_prompt(
            prompt,
            plan=plan,
            conversation_context=conversation_context,
            founder_context=founder_context,
            workspace_summary=workspace_summary,
            pending_approvals=pending_approvals,
            active_projects=active_projects,
            running_tasks=running_tasks,
            is_first_turn=is_first_turn,
        )

        # Try providers via the formal abstraction first.
        for provider in self._providers:
            try:
                content = provider.complete(system_prompt, user_prompt)
                if content:
                    sanitized = self._sanitize_provider_reply(content)
                    if sanitized:
                        return sanitized
            except Exception:
                continue

        # Legacy fallback: direct openai client (used when provider abstraction
        # is unavailable, e.g. in isolated test environments that patch
        # _openai_client directly).
        if self._openai_client and not self._providers:
            try:
                completion = self._openai_client.chat.completions.create(
                    model=self._model_name,
                    temperature=0.2,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                )
                content = (getattr(completion.choices[0].message, "content", None) or "").strip()
                sanitized = self._sanitize_provider_reply(content)
                if sanitized:
                    return sanitized
            except Exception:
                pass

        return None

    def _normalize_for_classification(self, text: str) -> str:
        """Normalize Arabic text and common Latinized transliterations."""
        t = self._normalize(text.lower())
        replacements = {
            "kayf": "كيف",
            "kif": "كيف",
            "atla3": "أطلق",
            "atlaq": "أطلق",
            "atlak": "أطلق",
            "atla9": "أطلق",
            "tla3": "أطلق",
            "launch": "أطلق",
            "start": "ابدأ",
            "go": "ابدأ",
            "live": "تشغيل",
            "astathmir": "استثمر",
            "astathmer": "استثمر",
            "ishtathmir": "استثمر",
            "astathmar": "استثمر",
            "ta3kar": "تذكر",
            "tazkar": "تذكر",
            "athkar": "تذكر",
            "anshi2": "أنشئ",
            "anshi": "أنشئ",
            "ansh2": "أنشئ",
            "anshie": "أنشئ",
            "create": "أنشئ",
            "laysh": "لماذا",
            "ta2akhar": "تأخر",
            "mawqa2": "موقع",
            "mawq3": "موقع",
            "ma3loma": "معلومة",
            "aldhakira": "الذاكرة",
            "almontaj": "المنتج",
            "mashro3": "مشروع",
            "mashru": "مشروع",
            "mashroo": "مشروع",
            "mashru3": "مشروع",
        }
        for src, dst in replacements.items():
            t = t.replace(src, dst)
        return t

    # ── Perception ────────────────────────────────────────────────────────────

    def perceive(self, query: str) -> PerceptionResult:
        """Classify the request type and detect ambiguity."""
        q = self._normalize_for_classification(query)
        q_words = set(re.findall(r"\w+", q))

        greeting_tokens = {"مرحبا", "اهلا", "أهلا", "سلام", "hello", "hi", "hey"}
        assistant_name_tokens = {"أمير", "امير", "ameer"}
        q_words_only = re.sub(r"[^\u0621-\u064Aa-zA-Z0-9]", "", q).strip()
        is_name_call = q_words_only in {self._normalize_for_classification(n.lower()) for n in assistant_name_tokens}
        is_greeting = q.strip() in greeting_tokens or any(token in q_words for token in {"hello", "hi", "hey", "مرحبا", "اهلا", "أهلا", "سلام"})
        if is_name_call or is_greeting:
            return PerceptionResult(
                request_type="question",
                confidence=1.0,
                ambiguous=False,
                clarification_needed=False,
                clarification_question=None,
            )

        scores: Dict[str, int] = {}
        boosts = {
            "planning": ["أطلق", "ابدأ", "انطلق", "launch", "start", "go live", "خطوات", "خطة", "plan", "roadmap"],
            "execution": ["أنشئ", "create", "write", "build", "generate", "ملف", "new", "أضف", "احذف", "عدل", "أرسل", "شغل", "نفذ", "مشروع", "موقع", "project", "website"],
            "decision": ["استثمر", "أوافق", "قرر", "decide", "should i", "هل يجب", "أختار", "أقبل", "أرفض"],
            "memory": ["تذكر", "احفظ", "remember", "save", "لا تنس", "سجل"],
            "analysis": ["لماذا", "سبب", "why", "explain", "تأخر", "فشل", "نجح", "نتيجة", "تحليل"],
            "creative": ["اقترح", "اسم", "فكرة", "suggest", "brainstorm", "ideas", "ابتكر"],
        }

        execution_markers = [
            "أنشئ", "انشئ", "إنشاء", "اكتب", "create", "write", "build", "make", "new file", "new project", "new website",
            "ملف", "موقع", "مشروع", "أضف", "append", "update", "modify", "عدل", "تعديل", "سطر", "insert", "أدخل"
        ]
        if any(keyword in q for keyword in execution_markers):
            scores["execution"] = 12
        else:
            scores["execution"] = 0

        for rtype, keywords in REQUEST_TYPES.items():
            # Normalize keywords too for fair comparison
            score = 0
            for kw in keywords:
                norm_kw = self._normalize_for_classification(kw.lower())
                # Match as substring or word
                if norm_kw in q or norm_kw in q_words:
                    score += 3 if len(norm_kw) > 3 and " " in norm_kw else 2 if len(norm_kw) > 3 else 1

            for boost_kw in boosts.get(rtype, []):
                norm_kw = self._normalize_for_classification(boost_kw.lower())
                if norm_kw in q or norm_kw in q_words:
                    score += 2
            scores[rtype] = score

        best_type = max(scores, key=lambda k: scores[k])
        best_score = scores[best_type]
        total = sum(scores.values())

        if best_type == "question" and scores.get("execution", 0) >= 12:
            best_type = "execution"
            best_score = scores["execution"]

        confidence = (best_score / total) if total > 0 else 0.0
        ambiguous = confidence < 0.4 or best_score == 0

        clarification_needed = ambiguous and len(q_words) < 4
        clarification_question = (
            "هل تريد مني تحليل الموضوع بعمق، أم تريد إجابة سريعة، أم تريد تنفيذ شيء محدد؟"
            if clarification_needed else None
        )

        return PerceptionResult(
            request_type=best_type if best_score > 0 else "question",
            confidence=round(confidence, 2),
            ambiguous=ambiguous,
            clarification_needed=clarification_needed,
            clarification_question=clarification_question,
        )

    # ── Context Linking ───────────────────────────────────────────────────────

    def link_context(self, query: str, documents: list) -> tuple[List[ContextLink], str]:
        """Find cross-project links relevant to the query."""
        q = self._normalize_for_classification(query)
        links: List[ContextLink] = []

        project_signals = {
            "حلم الندى": ["حلم", "ندى", "dream", "nada"],
            "أمير": ["امير", "ameer", "المشروع", "النظام"],
            "الميزانية العامة": ["ميزانية", "تمويل", "مال", "finance", "budget"],
            "الصحة": ["صحة", "نوم", "رياضة", "health", "sleep"],
        }

        for proj, signals in project_signals.items():
            if any(s in q for s in signals):
                relevance = "مرتبط مباشرة بالسؤال"
                constraint = None
                if proj == "الميزانية العامة":
                    constraint = "تأكد من السيولة قبل أي قرار مالي"
                links.append(ContextLink(project=proj, relevance=relevance, constraint=constraint))

        context_summary = (
            f"السياق يشمل {len(links)} مشروع ذو صلة: {', '.join(c.project for c in links)}."
            if links else "لم يُكتشف ارتباط مباشر بمشاريع أخرى."
        )
        return links, context_summary

    # ── Agent Selection ───────────────────────────────────────────────────────

    def select_agents(self, query: str, request_type: str) -> AgentSelection:
        """Choose the best specialist agent(s) for this request."""
        q = self._normalize_for_classification(query)

        direct_core_markers = [
            "من أنت",
            "من انت",
            "عرف بنفسك",
            "ماذا تستطيع",
            "ما دورك",
            "كيف تعمل",
            "هل تفهمني",
            "هل تعرفني",
            "who are you",
            "what can you do",
            "how do you work",
            "do you understand me",
        ]
        normalized_core_markers = [self._normalize_for_classification(marker) for marker in direct_core_markers]
        if any(marker in q for marker in normalized_core_markers):
            return AgentSelection(
                primary_agent="ameer_core",
                supporting_agents=[],
                reasoning="هذا سؤال مباشر عن هوية أمير أو دوره التنفيذي، لذا يتولاه أمير بنفسه دون تفويض.",
            )

        scores: Dict[str, int] = {}
        for agent_id, meta in AGENT_CATALOG.items():
            score = 0
            for kw in meta["keywords"]:
                norm_kw = self._normalize(kw.lower())
                if norm_kw in q:
                    score += 2 if len(norm_kw) > 3 else 1
            scores[agent_id] = score

        # Fallback to type-based agent
        type_defaults = {
            "planning": "project_manager",
            "decision": "investment_agent",
            "execution": "code_agent",
            "memory": "memory_agent",
            "analysis": "research_agent",
            "creative": "design_agent",
            "question": "research_agent",
        }

        sorted_agents = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        primary = sorted_agents[0][0] if sorted_agents[0][1] > 0 else type_defaults.get(request_type, "research_agent")
        supporting = [a for a, s in sorted_agents[1:3] if s > 0 and a != primary]

        reasoning = (
            f"اخترت {AGENT_CATALOG[primary]['description']} لأن الكلمات المفتاحية تشير إليه."
            if scores.get(primary, 0) > 0
            else f"لم تتطابق كلمات واضحة، لذا استخدمت الوكيل الافتراضي لنوع '{request_type}'."
        )

        return AgentSelection(
            primary_agent=primary,
            supporting_agents=supporting,
            reasoning=reasoning,
        )

    # ── Planning ──────────────────────────────────────────────────────────────

    def build_plan(self, query: str, request_type: str, agent: AgentSelection) -> tuple[str, List[str]]:
        """Decide if this needs a direct answer or a multi-step plan."""
        simple_types = {"question", "memory"}
        if request_type in simple_types:
            return "direct", [f"أجب مباشرة باستخدام {agent.primary_agent}"]

        steps = []
        if request_type == "execution":
            steps = [
                "فهم المتطلبات بدقة",
                "فحص الملفات والموارد المتاحة",
                "تحضير الخطوات التنفيذية",
                "انتظار موافقة المؤسس",
                "التنفيذ خطوة بخطوة",
                "التحقق من النتيجة",
            ]
        elif request_type == "planning":
            steps = [
                "جمع المعلومات من المشاريع ذات الصلة",
                "تحليل القيود الحالية",
                "اقتراح خطة مرحلية",
                "مناقشة الخيارات مع المؤسس",
            ]
        elif request_type == "decision":
            steps = [
                "تجميع البيانات من الذاكرة والمشاريع",
                "تحليل المخاطر والفرص",
                "تقديم توصية موضوعية",
                "الانتظار لقرار المؤسس النهائي",
            ]
        elif request_type == "analysis":
            steps = [
                "قراءة الملفات ذات الصلة",
                "ربط المعلومات عبر المشاريع",
                "تحليل الأسباب والنتائج",
                "صياغة التحليل بوضوح",
            ]
        else:
            steps = ["معالجة الطلب", "صياغة الإجابة المناسبة"]

        return "multi_step", steps

    # ── Reflection ────────────────────────────────────────────────────────────

    def reflect(self, query: str, request_type: str) -> tuple[bool, Optional[str]]:
        """Decide if this interaction should be saved to memory."""
        memory_worthy_types = {"decision", "memory", "planning"}
        important_signals = ["تذكر", "احفظ", "مهم", "remember", "save", "important"]
        q = self._normalize_for_classification(query)

        should_remember = (
            request_type in memory_worthy_types
            or any(s in q for s in important_signals)
        )

        note = None
        if should_remember:
            note = f"حفظ: {request_type.upper()} — {query[:80]}"

        return should_remember, note

    def _extract_memory_fact(self, query: str, plan: ExecutivePlan | None = None) -> Optional[str]:
        if plan and getattr(plan, "memory_note", None):
            note = str(plan.memory_note).strip()
            if note:
                return note

        q = (query or "").strip()
        patterns = [
            r"(?:تذكر|ذكر|احفظ|save|remember)\s+(?:أن|that|this|me|my|i)\s*(.+)",
            r"(?:أحب\s+أن\s+تتذكر|أريد\s+أن\s+تتذكر|أريد\s+أن\s+أحفظ|أحب\s+أن\s+أحفظ)\s*(.+)",
            r"(?:remember|save)\s+(?:that|this)\s*(.+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, q, flags=re.IGNORECASE | re.UNICODE)
            if match:
                fact = match.group(1).strip(" .،؟")
                if fact:
                    return fact

        if any(token in q.lower() for token in ["تذكر", "remember", "save", "احفظ"]):
            return q
        return None

    def _persist_memory_fact(self, fact: str, workspace_root: str | None = None) -> dict:
        root = workspace_root or os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        memory_dir = os.path.join(root, "04_Memory")
        memory_file = os.path.join(memory_dir, "Preferences.md")
        if not self._check_write_allowed(memory_file, root):
            return {"saved": False, "file": "04_Memory/Preferences.md", "fact": fact, "reason": "write_not_permitted"}
        os.makedirs(memory_dir, exist_ok=True)

        for attempt in range(2):
            try:
                if not os.path.exists(memory_file):
                    with open(memory_file, "w", encoding="utf-8") as handle:
                        handle.write("# Preferences\n\n")

                with open(memory_file, "r", encoding="utf-8") as handle:
                    content = handle.read()

                note = f"- {datetime.now(timezone.utc).strftime('%Y-%m-%d')} — {fact}"
                if note in content:
                    return {"saved": True, "file": "04_Memory/Preferences.md", "fact": fact, "reason": "already_present"}

                if "## User Notes" not in content:
                    content = content.rstrip() + "\n\n## User Notes\n"
                else:
                    content = content.rstrip() + "\n"

                content += note + "\n"
                with open(memory_file, "w", encoding="utf-8") as handle:
                    handle.write(content)

                return {"saved": True, "file": "04_Memory/Preferences.md", "fact": fact, "reason": "saved"}
            except Exception:
                if attempt == 1:
                    return {"saved": False, "file": "04_Memory/Preferences.md", "fact": fact, "reason": "write_failed"}
        return {"saved": False, "file": "04_Memory/Preferences.md", "fact": fact, "reason": "write_failed"}

    def _persist_execution_outcome(self, query: str, execution_result: dict, workspace_root: str | None = None) -> dict:
        summary = (execution_result or {}).get("summary") or "تم تنفيذ طلب بدون ملخص مفصل."
        status = (execution_result or {}).get("status") or "unknown"
        outcome = {
            "query": (query or "").strip(),
            "status": status,
            "summary": summary,
            "actions": execution_result.get("actions", []),
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        serialized = json.dumps(outcome, ensure_ascii=False)
        return self._persist_memory_fact(f"Execution Outcome: {serialized}", workspace_root=workspace_root)

    def _extract_file_operation(self, query: str) -> tuple[Optional[str], Optional[str], str]:
        q = (query or "").strip()
        filename = None
        content = None
        operation = "create"
        q_lower = q.lower()

        update_markers = [
            "أضف", "append", "add line", "insert", "سطر", "عدّل", "update", "modify", "تعديل",
            "أدخل", "add", "append to", "update file", "edit", "write to", "append line"
        ]
        read_markers = ["اقرأ", "read", "show", "اعرض", "contents", "محتوى", "content", "عرض"]

        if any(token in q_lower for token in update_markers):
            operation = "update"
        elif any(token in q_lower for token in read_markers):
            operation = "read"

        patterns = [
            r"(?:file|ملف)(?:\s+name|\s+اسم|\s+باسم)?\s+([A-Za-z0-9._/-]+)",
            r"(?:named|اسم|باسم)\s+([A-Za-z0-9._/-]+)",
            r"(?:باسم|اسم)\s+([A-Za-z0-9._/-]+)",
            r"(?:in|في)\s+([A-Za-z0-9._/-]+\.md|[A-Za-z0-9._/-]+\.txt|[A-Za-z0-9._/-]+\.py)",
            r"([A-Za-z0-9._/-]+\.md|[A-Za-z0-9._/-]+\.txt|[A-Za-z0-9._/-]+\.py)",
        ]
        for pattern in patterns:
            match = re.search(pattern, q, flags=re.IGNORECASE)
            if match:
                filename = match.group(1).strip()
                break

        content_patterns = [
            r"(?:contains|contain|يحتوي\s+على|يحتوي)\s*(.+)",
            r"(?:with|مع)\s*(.+)",
            r"(?:says|يقول|قال)\s*['\"]?(.+?)['\"]?$",
            r"(?:says\s+\"|يقول\s+\")(.+?)(?:\"|$)",
            r"(?:says\s+'|يقول\s+')(.+?)(?:'|$)",
        ]
        for pattern in content_patterns:
            match = re.search(pattern, q, flags=re.IGNORECASE | re.UNICODE)
            if match:
                content = match.group(1).strip(" .،؟")
                break

        if not filename:
            return None, None, operation
        if not content and operation != "read":
            content = "تم إنشاء هذا الملف عبر Ameer."
        return filename, content, operation

    # Directories (relative to workspace root) that file-write operations may target.
    # Any path outside these prefixes is rejected to prevent path-traversal attacks.
    _ALLOWED_WRITE_PREFIXES: tuple[str, ...] = (
        "04_Memory",
        "09_Assets/web/modules",
        ".ameer",
    )

    def _check_write_allowed(self, target_path: str, root: str) -> bool:
        """Return True only if *target_path* sits inside an allowed write prefix."""
        abs_root = os.path.abspath(root)
        abs_target = os.path.abspath(target_path)
        # Ensure the target is inside the workspace at all.
        try:
            rel = os.path.relpath(abs_target, abs_root).replace("\\", "/")
        except ValueError:
            return False
        if rel.startswith(".."):
            return False
        return any(rel == prefix or rel.startswith(prefix + "/") for prefix in self._ALLOWED_WRITE_PREFIXES)

    def _create_file(self, filename: str, content: str, workspace_root: str | None = None) -> dict:
        root = workspace_root or os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        target_path = os.path.abspath(os.path.join(root, filename))
        if not self._check_write_allowed(target_path, root):
            return {
                "status": "blocked",
                "path": target_path,
                "relative_path": os.path.relpath(target_path, root).replace("\\", "/"),
                "content_preview": content[:120],
                "reason": "write_not_permitted_outside_allowed_paths",
            }
        for attempt in range(2):
            try:
                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                with open(target_path, "w", encoding="utf-8") as handle:
                    handle.write(content)
                return {
                    "status": "created",
                    "path": target_path,
                    "relative_path": os.path.relpath(target_path, root).replace("\\", "/"),
                    "content_preview": content[:120],
                }
            except Exception:
                if attempt == 1:
                    return {
                        "status": "failed",
                        "path": target_path,
                        "relative_path": os.path.relpath(target_path, root).replace("\\", "/"),
                        "content_preview": content[:120],
                    }
        return {
            "status": "failed",
            "path": target_path,
            "relative_path": os.path.relpath(target_path, root).replace("\\", "/"),
            "content_preview": content[:120],
        }

    def _append_to_existing_file(self, filename: str, content: str, workspace_root: str | None = None) -> dict:
        root = workspace_root or os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        target_path = Path(os.path.abspath(os.path.join(root, filename)))
        if not self._check_write_allowed(str(target_path), root):
            return {
                "status": "blocked",
                "path": str(target_path),
                "relative_path": os.path.relpath(target_path, root).replace("\\", "/"),
                "content_preview": content[:120],
                "reason": "write_not_permitted_outside_allowed_paths",
            }
        try:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            if target_path.exists():
                existing = target_path.read_text(encoding="utf-8")
                if content and content in existing:
                    return {
                        "status": "unchanged",
                        "path": str(target_path),
                        "relative_path": os.path.relpath(target_path, root).replace("\\", "/"),
                        "content_preview": existing[:120],
                    }
                if existing and not existing.endswith("\n"):
                    existing = existing + "\n"
                new_content = existing + content + "\n"
                target_path.write_text(new_content, encoding="utf-8")
                return {
                    "status": "updated",
                    "path": str(target_path),
                    "relative_path": os.path.relpath(target_path, root).replace("\\", "/"),
                    "content_preview": new_content[:120],
                }

            if not content:
                content = "تم إنشاء هذا الملف عبر Ameer."
            return self._create_file(filename, content, workspace_root=workspace_root)
        except Exception:
            return {
                "status": "failed",
                "path": str(target_path),
                "relative_path": os.path.relpath(target_path, root).replace("\\", "/"),
                "content_preview": content[:120],
            }

    def _read_text_file(self, path: Path) -> str:
        return path.read_text(encoding="utf-8")

    def _write_text_file(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def _extract_page_request(self, query: str) -> dict:
        q = (query or "").strip()
        default = {
            "page_key": None,
            "title": None,
            "label": None,
            "icon": "✨",
            "description": "صفحة جديدة أنشأها أمير.",
        }
        if not q:
            return default

        name_match = re.search(
            r"(?:صفحة|page)(?:\s+جديدة)?(?:\s+باسم|\s+اسمها|\s+اسم|\s+called|\s+named)?\s+[\"'“”]?([\u0600-\u06FFA-Za-z0-9 _-]+)[\"'“”]?",
            q,
            flags=re.IGNORECASE,
        )
        label = name_match.group(1).strip() if name_match else None
        if label:
            stop_markers = [
                " أضفها",
                " اضفها",
                " حدث",
                " حدّث",
                " للموقع",
                " للتنقل",
                " ثم",
                " add it",
                " update",
                " then",
                " and ",
            ]
            lowered_label = label.lower()
            cut_positions = [lowered_label.find(marker) for marker in stop_markers if lowered_label.find(marker) != -1]
            if cut_positions:
                label = label[:min(cut_positions)].strip(" -_،.")
            label = re.sub(r"\s+", " ", label)
            page_key = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")
            if not page_key:
                page_key = f"page-{abs(hash(label)) % 10000}"
            default["page_key"] = page_key
            default["label"] = label
            default["title"] = label

        desc_match = re.search(r"(?:عن|حول|for|about)\s+(.+)$", q, flags=re.IGNORECASE)
        if desc_match:
            default["description"] = desc_match.group(1).strip(" .،؟") or default["description"]

        if any(token in q.lower() for token in ["موقع", "website", "site", "web"]):
            default["icon"] = "🌐"
        elif any(token in q.lower() for token in ["مشروع", "project"]):
            default["icon"] = "📁"

        return default

    def _render_workspace_module(self, page: dict) -> str:
        title = page["title"].replace("`", "'")
        description = page["description"].replace("`", "'")
        label = page["label"].replace("`", "'")
        ask_prompt = json.dumps(f"أعطني ملخصًا سريعًا عن صفحة {label} وما الذي تفعله الآن.", ensure_ascii=False)
        improve_prompt = json.dumps(f"اقترح تحسينات عملية لصفحة {label} ثم ابدأ بتنفيذ أول تحسين آمن داخل الواجهة.", ensure_ascii=False)
        return (
            "(function () {\n"
            f"  function create{page['page_key'].replace('-', ' ').title().replace(' ', '')}Module() {{\n"
            "    return {\n"
            "      render(container) {\n"
            "        if (!container) return;\n"
            "        container.innerHTML = `\n"
            "          <section class=\"module-card\" style=\"display:grid;gap:12px;\">\n"
            "            <div class=\"dashboard-hero\">\n"
            "              <div>\n"
            "                <div class=\"status-pill\">Generated Page</div>\n"
            f"                <h2>{title}</h2>\n"
            f"                <p>{description}</p>\n"
            "              </div>\n"
            f"              <div class=\"chip\">{label}</div>\n"
            "            </div>\n"
            "            <div class=\"dashboard-card\">\n"
            "              <h3>تم إنشاؤها عبر التنفيذ</h3>\n"
            "              <div class=\"subtle\">هذه الصفحة أضيفت تلقائيًا إلى الواجهة والتنقل.</div>\n"
            "              <div class=\"dashboard-actions\" style=\"margin-top:8px;\">\n"
            "                <button data-action=\"ask-page\" type=\"button\">اسأل أمير عن هذه الصفحة</button>\n"
            "                <button data-action=\"improve-page\" type=\"button\" style=\"background:var(--accent-2);color:white;\">نفّذ تحسينًا أوليًا</button>\n"
            "                <button data-action=\"open-chat\" type=\"button\" style=\"background:var(--panel-soft);color:var(--ink);border:1px solid var(--line);\">افتح المحادثة التنفيذية</button>\n"
            "              </div>\n"
            "            </div>\n"
            "          </section>\n"
            "        `;\n"
            f"        container.querySelector('[data-action=\"ask-page\"]')?.addEventListener('click', () => {{\n"
            "          if (window.AmeerWorkspaceShell && typeof window.AmeerWorkspaceShell.sendPrompt === 'function') {\n"
            f"            window.AmeerWorkspaceShell.sendPrompt({ask_prompt});\n"
            "          }\n"
            "        });\n"
            f"        container.querySelector('[data-action=\"improve-page\"]')?.addEventListener('click', () => {{\n"
            "          if (window.AmeerWorkspaceShell && typeof window.AmeerWorkspaceShell.sendPrompt === 'function') {\n"
            f"            window.AmeerWorkspaceShell.sendPrompt({improve_prompt});\n"
            "          }\n"
            "        });\n"
            "        container.querySelector('[data-action=\"open-chat\"]')?.addEventListener('click', () => {\n"
            "          if (window.AmeerWorkspaceShell && typeof window.AmeerWorkspaceShell.openPage === 'function') {\n"
            "            window.AmeerWorkspaceShell.openPage('executive-chat');\n"
            "          }\n"
            "        });\n"
            "      },\n"
            "      destroy(container) {\n"
            "        if (container) container.innerHTML = '';\n"
            "      }\n"
            "    };\n"
            "  }\n\n"
            "  window.AmeerWorkspaceModules = window.AmeerWorkspaceModules || {};\n"
            f"  window.AmeerWorkspaceModules['{page['page_key']}'] = create{page['page_key'].replace('-', ' ').title().replace(' ', '')}Module();\n"
            "})();\n"
        )

    def _append_unique_block(self, text: str, anchor: str, block: str) -> tuple[str, bool]:
        if block in text:
            return text, False
        if anchor not in text:
            raise ValueError(f"anchor_not_found:{anchor}")
        return text.replace(anchor, f"{anchor}{block}", 1), True

    def _insert_before_unique(self, text: str, marker: str, block: str) -> tuple[str, bool]:
        if block in text:
            return text, False
        if marker not in text:
            raise ValueError(f"marker_not_found:{marker}")
        return text.replace(marker, f"{block}{marker}", 1), True

    def _insert_into_named_block(self, text: str, declaration: str, closer: str, block: str) -> tuple[str, bool]:
        if block in text:
            return text, False

        start = text.find(declaration)
        if start == -1:
            raise ValueError(f"declaration_not_found:{declaration}")

        body_start = start + len(declaration)
        end = text.find(closer, body_start)
        if end == -1:
            raise ValueError(f"closer_not_found:{closer}")

        return text[:end] + block + text[end:], True

    def _execute_workspace_page_creation(self, query: str, workspace_root: str | None = None) -> dict:
        root = Path(workspace_root or os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
        page = self._extract_page_request(query)
        if not page.get("page_key"):
            return {
                "status": "failed",
                "reason": "page_name_not_detected",
                "detail": "تعذر تحديد اسم الصفحة المطلوبة من نص الطلب.",
            }

        page_key = page["page_key"]
        module_dir = root / "09_Assets" / "web" / "modules" / page_key
        module_file = module_dir / "index.js"
        index_file = root / "09_Assets" / "web" / "index.html"
        shell_file = root / "09_Assets" / "web" / "modules" / "shell.js"
        loader_file = root / "09_Assets" / "web" / "modules" / "loader.js"

        module_block = self._render_workspace_module(page)
        container_block = f"        <div id=\"view-{page_key}\" class=\"page-view\">\n          <div id=\"{page_key}Content\"></div>\n        </div>\n"
        nav_block = f"    {{ key: '{page_key}', label: '{page['label']}', icon: '{page['icon']}' }},\n"
        page_map_block = f"      {page_key}: ['{page['label']}', 'Ameer OS · {page['label']}'],\n"
        module_path_block = f"    {page_key}: './modules/{page_key}/index.js',\n"
        host_id_block = f"    {page_key}: '{page_key}Content',\n"

        created = []
        verified = []
        try:
            if not module_file.exists():
                self._write_text_file(module_file, module_block)
                created.append(str(module_file.relative_to(root)).replace("\\", "/"))
            else:
                existing = self._read_text_file(module_file)
                if page_key not in existing:
                    self._write_text_file(module_file, module_block)
                    created.append(str(module_file.relative_to(root)).replace("\\", "/"))

            index_text = self._read_text_file(index_file)
            index_text, _ = self._insert_before_unique(index_text, "      </div>\n\n      <div class=\"composer\">", container_block)
            self._write_text_file(index_file, index_text)

            shell_text = self._read_text_file(shell_file)
            shell_text, _ = self._insert_into_named_block(shell_text, "const navItems = [\n", "];\n", nav_block)
            shell_text, _ = self._insert_into_named_block(shell_text, "const pageMap = {\n", "};\n", page_map_block)
            self._write_text_file(shell_file, shell_text)

            loader_text = self._read_text_file(loader_file)
            loader_text, _ = self._insert_into_named_block(loader_text, "const modulePaths = {\n", "};\n", module_path_block)
            loader_text, _ = self._insert_into_named_block(loader_text, "const hostIds = {\n", "};\n", host_id_block)
            self._write_text_file(loader_file, loader_text)

            for verify_path in [module_file, index_file, shell_file, loader_file]:
                if verify_path.exists():
                    verified.append(str(verify_path.relative_to(root)).replace("\\", "/"))

            return {
                "status": "completed",
                "page_key": page_key,
                "title": page["title"],
                "label": page["label"],
                "created": created,
                "verified": verified,
            }
        except Exception as exc:
            return {
                "status": "failed",
                "page_key": page_key,
                "reason": "workspace_page_update_failed",
                "detail": str(exc),
                "created": created,
                "verified": verified,
            }

    def _execute_plan(self, query: str, plan: ExecutivePlan | None = None, workspace_root: str | None = None) -> dict:
        result = {
            "status": "idle",
            "actions": [],
            "memory": None,
            "file": None,
            "plan": None,
            "tool_calls": [],
            "summary": "",
            "progress": [],
            "verification": [],
            "execution": None,
        }

        if not plan:
            return result

        steps = [str(step).lower() for step in (plan.steps or [])]
        query_lower = (query or "").lower()
        has_memory_intent = any(token in query_lower for token in ["تذكر", "remember", "save", "احفظ", "ذاكرة", "memory", "recall"])
        has_file_intent = any(token in query_lower for token in ["ملف", "file", "أنشئ", "create", "اكتب", "باسم", "named", "contains", "يحتوي", "أضف", "append", "update", "modify", "read", "اقرأ", "سطر", "edit", "insert", "add line"])
        has_planning_intent = any(token in query_lower for token in ["خطة", "plan", "خطوات", "ابدأ", "start", "planning"])
        has_page_intent = any(token in query_lower for token in ["صفحة", "page", "navigation", "nav", "site", "website", "الموقع", "التنقل"])

        progress = [
            self._execution_step("analyze_request", "running", "جارٍ تحليل الطلب التنفيذي"),
        ]
        result["progress"] = progress
        self._update_step(progress, "analyze_request", "succeeded", "تم تحديد نوع التنفيذ المطلوب")

        # Only auto-save when the user explicitly asks to save/remember something.
        # We use whole-word matching to avoid false positives like "سجلتها" → "سجل".
        # plan.should_remember may be set by classifier heuristics that can fire on
        # substring matches; the token check here guards against that.
        _query_words = set(re.findall(r"\w+", query_lower))
        _explicit_save_tokens = {"تذكر", "احفظ", "remember", "save"}
        has_explicit_save_request = bool(_query_words & _explicit_save_tokens)
        should_capture_memory = (
            plan is not None
            and bool(getattr(plan, "should_remember", False))
            and has_explicit_save_request
            and bool((query or "").strip())
        )
        if should_capture_memory:
            self._update_step(progress, "persist_request_memory", "running", "جارٍ حفظ سجل الطلب")
            fact = self._extract_memory_fact(query, plan) or f"محادثة: {(query or '').strip()[:80]}"
            if fact:
                memory_result = self._persist_memory_fact(fact, workspace_root=workspace_root)
                result["memory"] = memory_result
                result["actions"].append({"tool": "memory.save", "status": "completed" if memory_result.get("saved") else "failed"})
                result["tool_calls"].append("memory.save")
                self._update_step(progress, "persist_request_memory", "succeeded" if memory_result.get("saved") else "failed", memory_result.get("reason", ""))

        # EC-002: Memory Governance — WRITE only on explicit save intent.
        # has_memory_intent fires on read words like "تذكر" (recall/remember).
        # Gating on has_explicit_save_request ensures READ never becomes WRITE.
        if has_explicit_save_request and (has_memory_intent or any(token in " ".join(steps) for token in ["remember", "save", "تذكر", "ذاكرة", "احفظ"])):
            fact = self._extract_memory_fact(query, plan)
            if fact and not result["memory"]:
                self._update_step(progress, "persist_memory_fact", "running", "جارٍ حفظ المعلومة المطلوبة")
                memory_result = self._persist_memory_fact(fact, workspace_root=workspace_root)
                result["memory"] = memory_result
                result["actions"].append({"tool": "memory.save", "status": "completed" if memory_result.get("saved") else "failed"})
                result["tool_calls"].append("memory.save")
                self._update_step(progress, "persist_memory_fact", "succeeded" if memory_result.get("saved") else "failed", memory_result.get("reason", ""))

        if has_page_intent and any(token in query_lower for token in ["أضف", "add", "التنقل", "navigation", "الموقع", "site", "website", "صفحة", "page"]):
            self._update_step(progress, "create_workspace_page", "running", "جارٍ إنشاء الصفحة وربطها بالواجهة")
            execution_result = self._execute_workspace_page_creation(query, workspace_root=workspace_root)
            result["execution"] = execution_result
            execution_status = execution_result.get("status", "failed")
            detail = execution_result.get("detail") or execution_result.get("page_key") or ""
            self._update_step(progress, "create_workspace_page", "succeeded" if execution_status == "completed" else "failed", detail)
            result["actions"].append({"tool": "workspace.page.create", "status": execution_status, "result": execution_result})
            result["tool_calls"].append("workspace.page.create")
            if execution_status == "completed":
                result["verification"].append({
                    "name": "workspace_page_files_exist",
                    "status": "succeeded",
                    "checked": execution_result.get("verified", []),
                })
            else:
                result["verification"].append({
                    "name": "workspace_page_files_exist",
                    "status": "failed",
                    "checked": execution_result.get("verified", []),
                    "detail": execution_result.get("detail") or execution_result.get("reason"),
                })

        elif has_file_intent or any(token in " ".join(steps) for token in ["file", "create", "ملف", "أنشئ"]):
            self._update_step(progress, "create_file", "running", "جارٍ تنفيذ العملية على الملف المطلوب")
            filename, content, operation = self._extract_file_operation(query)
            if filename:
                if operation == "read":
                    target_path = Path(workspace_root or os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))) / filename
                    if target_path.exists():
                        file_result = {
                            "status": "read",
                            "path": str(target_path),
                            "relative_path": os.path.relpath(target_path, workspace_root or os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))).replace("\\", "/"),
                            "content_preview": target_path.read_text(encoding="utf-8")[:240],
                        }
                    else:
                        file_result = {"status": "missing", "path": str(target_path), "relative_path": filename, "content_preview": ""}
                elif operation == "update":
                    file_result = self._append_to_existing_file(filename, content or "", workspace_root=workspace_root)
                else:
                    file_result = self._create_file(filename, content or "", workspace_root=workspace_root)
                result["file"] = file_result
                result["actions"].append({"tool": "file.create", "status": file_result.get("status", "created")})
                result["tool_calls"].append("file.create")
                file_ok = file_result.get("status") in {"created", "updated", "read"} and os.path.exists(file_result.get("path", ""))
                result["verification"].append({
                    "name": "created_file_exists",
                    "status": "succeeded" if file_ok else "failed",
                    "checked": [file_result.get("relative_path")],
                })
                self._update_step(progress, "create_file", "succeeded" if file_ok else "failed", file_result.get("relative_path", ""))

        if has_planning_intent or any(token in " ".join(steps) for token in ["plan", "planning", "خطة", "خطوات"]):
            self._update_step(progress, "create_plan", "running", "جارٍ تجهيز خطة التنفيذ")
            result["plan"] = {
                "status": "planned",
                "steps": list(plan.steps or []),
                "goal": getattr(plan, "executive_message", "") or "إجراء خطة عملية",
            }
            result["actions"].append({"tool": "plan.create", "status": "completed"})
            result["tool_calls"].append("plan.create")
            self._update_step(progress, "create_plan", "succeeded", "تم تجهيز خطة قابلة للتنفيذ")

        if result["actions"]:
            failed_actions = [action for action in result["actions"] if action.get("status") in {"failed"}]
            result["status"] = "failed" if failed_actions else "completed"
            execution_payload = result.get("execution") or {}
            if execution_payload.get("status") == "completed":
                result["summary"] = f"تم إنشاء الصفحة {execution_payload.get('label') or execution_payload.get('page_key')} وربطها بالتنقل والتحقق من الملفات."
            elif result["memory"] or result["file"]:
                result["summary"] = "تم تنفيذ الإجراءات المطلوبة عبر محرك التنفيذ."
            else:
                result["summary"] = "تم إعداد خطة تنفيذ."

            # Only persist execution outcome for concrete actions (file creation, page
            # deployment, explicit memory write).  Generic plan-creation steps are
            # internal bookkeeping and should not be written to the user's memory store.
            _outcome_worthy_tools = {"file.create", "workspace.page.create", "memory.save"}
            has_outcome_worthy_action = any(
                a.get("tool") in _outcome_worthy_tools for a in result["actions"]
            )
            if has_outcome_worthy_action:
                self._update_step(progress, "persist_execution_outcome", "running", "جارٍ حفظ نتيجة التنفيذ")
                outcome_memory = self._persist_execution_outcome(query, result, workspace_root=workspace_root)
                result["outcome_memory"] = outcome_memory
                self._update_step(progress, "persist_execution_outcome", "succeeded" if outcome_memory.get("saved") else "failed", outcome_memory.get("reason", ""))

        return result

    def _build_execution_summary(self, query: str, plan: ExecutivePlan, execution_result: dict | None = None) -> str:
        if not execution_result:
            return ""

        file_result = execution_result.get("file") or {}
        memory_result = execution_result.get("memory") or {}
        plan_result = execution_result.get("plan") or {}

        if file_result.get("status") == "created":
            relative_path = file_result.get("relative_path") or file_result.get("path") or "الملف"
            return f"تم إنشاء الملف {relative_path} بنجاح."

        execution_payload = execution_result.get("execution") or {}
        if execution_payload.get("status") == "completed":
            label = execution_payload.get("label") or execution_payload.get("page_key") or "الصفحة"
            return f"تم إنشاء الصفحة {label}، إضافتها للموقع، تحديث التنقل، والتحقق من الملفات بنجاح."

        if memory_result.get("saved"):
            return "تم حفظ ملاحظة جديدة في الذاكرة."

        if plan_result.get("status") == "planned":
            steps = plan_result.get("steps") or []
            if steps:
                return f"تم وضع خطة تنفيذية: {' → '.join(steps[:3])}."

        return ""

    def _compose_local_reply(self, query: str, plan: ExecutivePlan, orchestrator_result: dict) -> str:
        # Greeting / name-call must be handled first, before any clarification gate.
        if orchestrator_result.get("intent") == "greeting":
            q_words_only = self._normalize_for_classification(
                re.sub(r"[^\u0621-\u064Aa-zA-Z0-9]", "", (query or "").lower()).strip()
            )
            assistant_name_forms = {"أمير", "امير", "ameer"}
            normalized_name_forms = {self._normalize_for_classification(n) for n in assistant_name_forms}
            if q_words_only in normalized_name_forms:
                return "أنا هنا. من أين نبدأ؟"
            return "نبدأ من أعلى نقطة أثرًا — ما الذي يحتاج قرارًا أو تقدمًا الآن؟"

        if plan.clarification_needed and plan.clarification_question:
            return f"قبل أن أكمل، أحتاج فهم قصدك: {plan.clarification_question}"

        if (getattr(plan, "request_type", None) == "memory") and (orchestrator_result.get("intent") == "memory"):
            memory_text = ""
            try:
                root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
                memory_path = os.path.join(root, "04_Memory", "Preferences.md")
                if os.path.exists(memory_path):
                    memory_text = Path(memory_path).read_text(encoding="utf-8")
            except Exception:
                memory_text = ""
            if "كلمة السر" in (query or "") or "password" in (query or "").lower() or "secret" in (query or "").lower():
                for line in memory_text.splitlines():
                    if "كلمة السر" in line or "password" in line.lower() or "secret" in line.lower():
                        return line.strip().lstrip("- ")
                return "لم أجد كلمة السر محفوظة في الذاكرة حتى الآن."
            if memory_text:
                return "لديّ ملاحظات محفوظة في الذاكرة. حددي ما تبحثين عنه وأجلب لك ما يخصه."

        if plan.guardian_status == "needs_approval":
            return (
                "هذا الطلب يتجاوز ما أستطيع تنفيذه مباشرة بالصيغة الحالية. "
                "إذا كان هدفك مشروعًا محددًا، أقترح مسارًا آمنًا يحقق نفس النتيجة."
            )

        if plan.guardian_status == "blocked":
            return (
                "هذا الطلب خارج النطاق الذي أستطيع العمل فيه الآن. "
                "أستطيع اقتراح بديل آمن يحقق الهدف دون المخاطرة."
            )

        results = orchestrator_result.get("results") or []
        if results:
            _log_pattern = re.compile(
                r"^-\s+\d{4}-\d{2}-\d{2}\s+[—\-]\s+(?:محادثة:|Execution Outcome:|حفظ:)",
            )
            for r in results:
                excerpt = (r.get("excerpt") or "").strip()
                if excerpt and len(excerpt) >= 60 and not _log_pattern.match(excerpt):
                    return excerpt[:260]

        return plan.executive_message or "أنا معك."

    def compose_final_reply(
        self,
        query: str,
        orchestrator_result: dict,
        documents: list,
        existing_plan: ExecutivePlan | None = None,
        execution_result: dict | None = None,
        conversation_context: str = "",
        founder_context: str = "",
        workspace_summary: str = "",
        pending_approvals: Optional[List[dict]] = None,
        active_projects: Optional[List[str]] = None,
        running_tasks: Optional[List[dict]] = None,
        is_first_turn: bool = False,
    ) -> tuple[str, str]:
        plan = existing_plan or self.think(
            query,
            documents,
            guardian_result=orchestrator_result.get("guardian", {}),
        )

        trusted_core_reply = self._compose_trusted_core_reply(orchestrator_result)
        if trusted_core_reply:
            return trusted_core_reply, "executive_brain_core"

        # ── EC-001: Guardian gate ─────────────────────────────────────────────
        # The Guardian/Policy Engine must run before reasoning, retrieval, or
        # response composition.  Any request that the guardian has flagged must
        # be rejected here — before any document lookup, provider call, or
        # reply assembly reaches the user.  Identity and greeting replies are
        # exempted because they are constitutional duties, not governed actions.
        if plan and getattr(plan, "guardian_status", "pass") == "needs_approval":
            reason = (orchestrator_result.get("guardian") or {}).get("reason") or plan.guardian_reason
            return (
                "لا أستطيع تنفيذ هذا الطلب بصيغته الحالية لأنه يتجاوز حدود التشغيل المسموح بها. "
                "إذا كان هدفك مشروعًا أو مهمة عملية، أستطيع اقتراح طريقة آمنة تحقق نفس النتيجة."
            ), "guardian_gate"

        if plan and getattr(plan, "guardian_status", "pass") == "blocked":
            return (
                "هذا الطلب خارج النطاق الذي أستطيع العمل فيه الآن. "
                "أستطيع اقتراح بديل آمن يحقق الهدف دون المخاطرة."
            ), "guardian_gate"

        # Greetings are handled locally — no need to call the AI provider.
        if orchestrator_result.get("intent") == "greeting":
            reply = self._compose_local_reply(query, plan, orchestrator_result)
            return reply, "executive_brain_local"

        # For actual file/page execution, surface the concrete result before calling the LLM.
        # (The LLM cannot report "file created successfully" if it didn't do the creation.)
        execution_engine = execution_result or {}
        has_real_execution = (
            (execution_engine.get("file") or {}).get("status") in {"created", "updated"}
            or (execution_engine.get("execution") or {}).get("status") == "completed"
        )
        if plan and getattr(plan, "request_type", None) == "execution" and has_real_execution:
            execution_summary = self._build_execution_summary(query, plan, execution_result)
            if execution_summary:
                return execution_summary, "executive_brain_execution"

        # For all other requests (including planning and memory reads) try the LLM first
        # so the user gets a real, synthesised answer — not a generic internal summary.
        provider_reply = self._call_provider(
            query,
            plan=plan,
            conversation_context=conversation_context,
            founder_context=founder_context,
            workspace_summary=workspace_summary,
            pending_approvals=pending_approvals,
            active_projects=active_projects,
            running_tasks=running_tasks,
            is_first_turn=is_first_turn,
        )
        if provider_reply:
            return provider_reply, "executive_brain_provider"

        # LLM unavailable — fall back to execution summary only for concrete execution actions
        # (file created, page deployed, explicit memory write).  Planning queries fall
        # through to _compose_local_reply so they can surface real document excerpts
        # instead of generic internal process steps.
        if plan and getattr(plan, "request_type", None) in {"execution", "memory"}:
            execution_summary = self._build_execution_summary(query, plan, execution_result)
            if execution_summary:
                return execution_summary, "executive_brain_execution"

        reply = self._compose_local_reply(query, plan, orchestrator_result)
        return reply, "executive_brain_local"

    # ── Main Think Method ─────────────────────────────────────────────────────

    def think(
        self,
        query: str,
        documents: list,
        guardian_result: dict | None = None,
        routing_hint: dict | None = None,
    ) -> ExecutivePlan:
        """
        Full thinking cycle.
        Returns ExecutivePlan with all layers populated.
        """

        # 1. Perceive
        hinted_type = None
        if routing_hint:
            hinted_type = routing_hint.get("intent") or routing_hint.get("request_type")

        if not self._single_brain_mode and hinted_type in {"greeting", "identity", "project", "memory", "knowledge_lookup", "execution"}:
            request_type_map = {
                "greeting": "question",
                "identity": "question",
                "project": "planning",
                "memory": "memory",
                "knowledge_lookup": "question",
                "execution": "execution",
            }
            routed_perception = PerceptionResult(
                request_type=request_type_map.get(hinted_type, "question"),
                confidence=1.0,
                ambiguous=False,
                clarification_needed=False,
                clarification_question=None,
            )
            lexical_perception = self.perceive(query)
            if lexical_perception.request_type == "execution" and lexical_perception.confidence >= 0.3:
                perception = lexical_perception
            else:
                perception = routed_perception
        else:
            perception = self.perceive(query)

        # 2. Context
        links, context_summary = self.link_context(query, documents)

        # 3. Agent Selection
        if hinted_type == "identity":
            agent_sel = AgentSelection(
                primary_agent="ameer_core",
                supporting_agents=[],
                reasoning="أسئلة الهوية والدور التنفيذي تُدار داخل Ameer Core مباشرة.",
            )
        elif hinted_type == "greeting":
            agent_sel = AgentSelection(
                primary_agent="ameer_core",
                supporting_agents=[],
                reasoning="التحية والنداء المباشر لا تحتاج وكيلًا متخصصًا.",
            )
        else:
            hinted_agent = routing_hint.get("agent") if routing_hint else None
            if hinted_agent and perception.request_type != "execution" and not self._single_brain_mode:
                agent_sel = AgentSelection(
                    primary_agent=hinted_agent,
                    supporting_agents=[],
                    reasoning="تم اختيار المنفذ من طبقة Router مع بقاء أمير صاحب القرار والرد النهائي.",
                )
            else:
                agent_sel = self.select_agents(query, perception.request_type)

        # 4. Planning
        plan_type, steps = self.build_plan(query, perception.request_type, agent_sel)

        # 5. Guardian
        grd = guardian_result or {}
        g_status = grd.get("status", "pass")
        g_reason = grd.get("reason", "لا توجد مخاطر مرصودة.")
        autonomy = "act_autonomously" if g_status == "pass" else "suggest"

        # 6. Reflection
        should_remember, memory_note = self.reflect(query, perception.request_type)

        # 7. Compose executive message
        if perception.clarification_needed:
            msg = f"سؤالك غير واضح تمامًا. {perception.clarification_question}"
        elif g_status == "needs_approval":
            msg = (
                f"لاحظت أن هذا الطلب يحتاج موافقة منك. "
                f"السبب: {g_reason}. هل تؤكد المتابعة؟"
            )
        else:
            if plan_type == "direct":
                msg = "حاضر، سأجيبك الآن بصفتي العقل التنفيذي الأساسي."
            else:
                msg = f"سأعمل على طلبك خطوة بخطوة."

        return ExecutivePlan(
            request_type=perception.request_type,
            ambiguous=perception.ambiguous,
            clarification_needed=perception.clarification_needed,
            clarification_question=perception.clarification_question,
            context_links=[{"project": c.project, "relevance": c.relevance, "constraint": c.constraint} for c in links],
            context_summary=context_summary,
            plan_type=plan_type,
            steps=steps,
            selected_agent=agent_sel.primary_agent,
            supporting_agents=agent_sel.supporting_agents,
            agent_reasoning=agent_sel.reasoning,
            guardian_status=g_status,
            guardian_reason=g_reason,
            autonomy_level=autonomy,
            should_remember=should_remember,
            memory_note=memory_note,
            executive_message=msg,
        )

    def get_reasoning_output(self, query: str, documents: list, guardian_result: dict | None = None, routing_hint: dict | None = None) -> dict:
        """
        P0.7 — Reasoning-only interface for the Executive Brain.

        Returns structured internal state only; produces no visible user text.
        The Executive Conversation Engine is the sole owner of the final reply.
        """
        plan = self.think(query, documents, guardian_result=guardian_result, routing_hint=routing_hint)
        reasoning = {
            "request_type": plan.request_type,
            "plan_type": plan.plan_type,
            "steps": plan.steps,
            "context_summary": plan.context_summary,
            "agent_reasoning": plan.agent_reasoning,
            "guardian_status": plan.guardian_status,
            "guardian_reason": plan.guardian_reason,
            "autonomy_level": plan.autonomy_level,
            "should_remember": plan.should_remember,
        }
        executive_state = {
            "selected_agent": plan.selected_agent,
            "supporting_agents": plan.supporting_agents,
            "context_links": plan.context_links,
            "ambiguous": plan.ambiguous,
            "clarification_needed": plan.clarification_needed,
            "clarification_question": plan.clarification_question,
            "memory_note": plan.memory_note,
        }
        return {
            "reasoning": reasoning,
            "executive_state": executive_state,
            "_plan": plan,
        }
