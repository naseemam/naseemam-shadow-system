from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
import re
import sys
import uuid
from typing import Callable, Dict, List


CODE_ROOT = os.path.dirname(__file__)
if CODE_ROOT not in sys.path:
    sys.path.insert(0, CODE_ROOT)

from agents.base import AgentContext, AgentOutput
from agents.registry import AGENTS, AGENT_CAPABILITIES
from adapters.agent_brain_adapter import AgentBrainAdapter


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


ROUTE_AGENT_MAP = {
    "greeting": "greeting_agent",
    "identity": "ameer_core",
    "project": "project_agent",
    "memory": "memory_agent",
    "onboarding": "memory_agent",
    "execution": "project_agent",
    "knowledge_lookup": "research_agent",
}

CORE_ROUTE_CAPABILITIES = {
    "ameer_core": {
        "description": "Ameer Core handles identity, executive framing, and direct founder-facing replies.",
        "primary_sources": [
            "01_docs/ameer_constitution_v0.1.md",
            "01_docs/vision.md",
            "04_memory/founder.md",
        ],
        "capabilities": [
            "الهوية الأساسية",
            "الرد التنفيذي المباشر",
            "توضيح دور أمير وعلاقته بالمؤسس",
        ],
    }
}


@dataclass
class OrchestratorConfig:
    max_excerpt_chars: int = 240
    window_chars: int = 120


@dataclass
class SourcePolicy:
    route: str
    keywords: List[str]
    priority_groups: List[List[str]]
    force_first_group: bool = False


class AmeerOrchestrator:
    """Lightweight reasoning layer with conversation state, executive-style planning, and response shaping."""

    def __init__(
        self,
        documents: List[Dict[str, str]],
        score_fn: Callable[[str, str], int],
        normalize_fn: Callable[[str], str],
        config: OrchestratorConfig | None = None,
    ) -> None:
        self.documents = documents
        self.score_fn = score_fn
        self.normalize_fn = normalize_fn
        self.config = config or OrchestratorConfig()
        self.policies = self._build_policies()
        self.agents = AGENTS
        self.agent_brain_adapter = AgentBrainAdapter()
        self.session_memory: Dict[str, Dict] = {}
        self.high_risk_action_terms = [
            "delete",
            "drop",
            "destroy",
            "wipe",
            "reset",
            "deploy",
            "publish",
            "push",
            "نفذ",
            "تشغيل",
            "احذف",
            "امسح",
            "انشر",
            "طبق",
            "نفّذ",
        ]
        self.explicit_approval_terms = [
            "approved",
            "approve",
            "i approve",
            "وافق",
            "موافق",
            "اعتماد",
            "موافقه",
        ]
        self.founder_identity_terms = [
            "founder",
            "naseem",
            "المؤسس",
            "الموسس",
            "المووسس",
            "نسيم",
        ]
        self._required_agent_fields = [
            "agent",
            "confidence",
            "reply_draft",
            "sources",
            "actions",
            "message",
            "response_data",
        ]

    def _validate_agent_output(self, agent_output) -> Dict[str, List[str] | bool]:
        missing = [field for field in self._required_agent_fields if not hasattr(agent_output, field)]
        return {
            "ok": len(missing) == 0,
            "missing_fields": missing,
        }

    def _build_policies(self) -> List[SourcePolicy]:
        # Priority rules come from Ameer Mind instructions.
        return [
            SourcePolicy(
                route="identity",
                keywords=["هويه", "identity", "باسورد", "password", "كلمه مرور", "الهوية"],
                priority_groups=[
                    ["04_memory/founder.md"],
                    ["01_docs/ameer_constitution_v0.1.md", "01_docs/vision.md", "04_memory/"],
                ],
                force_first_group=True,
            ),
            SourcePolicy(
                route="memory",
                keywords=["ذاكره", "memory", "memories", "تذكر", "ذكرى"],
                priority_groups=[["04_memory/"]],
                force_first_group=True,
            ),
            SourcePolicy(
                route="onboarding",
                keywords=["احفظ", "تذكر ان", "معلومة عني", "معلومه عني", "سأخبرك عني", "ساخبرك عني"],
                priority_groups=[["04_memory/", "01_docs/ameer_constitution_v0.1.md"]],
                force_first_group=False,
            ),
            SourcePolicy(
                route="project",
                keywords=["project", "مشروع", "plan", "master plan", "خطة", "منتج"],
                priority_groups=[
                    ["01_docs/master_plan.md"],
                    ["04_memory/projects.md", "02_research/", "03_architecture/", "06_code/"],
                ],
                force_first_group=True,
            ),
            SourcePolicy(
                route="investment",
                keywords=["investment", "استثمار", "finance", "تمويل", "ميزانية", "مال"],
                priority_groups=[
                    ["04_memory/finance.md"],
                    ["04_memory/investment.md", "04_memory/"],
                ],
                force_first_group=True,
            ),
            SourcePolicy(
                route="execution",
                keywords=["تنفيذ", "ننفذ", "نفذ", "execution", "implement", "architecture", "code", "build"],
                priority_groups=[
                    ["03_architecture/"],
                    ["06_code/"],
                ],
                force_first_group=False,
            ),
        ]

    def _is_identity_question(self, query: str) -> bool:
        q = self.normalize_fn(query.lower())
        normalized_terms = [self.normalize_fn(term.lower()) for term in [
            "من أنت",
            "من انت",
            "مين أنت",
            "عرف بنفسك",
            "حدثني عن نفسك",
            "ما اسمك",
            "ما اسمك؟",
            "وش أنت",
            "ماذا تستطيع",
            "ما دورك",
            "كيف تعمل",
            "ما هي حدودك",
            "من هو مؤسسك",
            "من مؤسسك",
            "من هو أمير",
            "who are you",
            "what can you do",
            "what are your limits",
            "how do you work",
            "who is your founder",
            "هل تفهمني",
            "هل تعرفني",
            "هل انت معي",
            "هل أنت معي",
            "do you understand me",
            "do you know me",
        ]]
        return any(term in q for term in normalized_terms)

    def _capabilities_for_executor(self, executor: str) -> Dict:
        if executor in CORE_ROUTE_CAPABILITIES:
            return CORE_ROUTE_CAPABILITIES[executor]
        return AGENT_CAPABILITIES.get(executor, {})

    def _build_core_identity_payload(self, query: str) -> AgentOutput:
        qn = self.normalize_fn(query.lower())
        founder_question = any(term in qn for term in [self.normalize_fn(term.lower()) for term in [
            "من هي نسيم",
            "من هو نسيم",
            "who is naseem",
            "المؤسس",
            "founder",
            "نسيم",
        ]])

        if founder_question:
            reply = "نسيم هي المؤسسة وصاحبة القرار، وأنا أعمل تحت سلطتها مباشرة."
            facts = {
                "subject": "founder",
                "name": "Naseem",
                "role": "Founder",
                "authority": "Final decision maker",
            }
        elif any(term in qn for term in [self.normalize_fn(term.lower()) for term in [
            "هل تفهمني",
            "هل تعرفني",
            "do you understand me",
            "do you know me",
        ]]):
            reply = "نعم، أفهمك ضمن ما تشاركينه معي. أستوعب هدفك وأعمل معك لتحقيقه."
            facts = {
                "subject": "ameer",
                "name": "Ameer",
                "role": "Executive Partner",
                "purpose": "Direct understanding and executive partnership",
            }
        elif any(term in qn for term in [self.normalize_fn(term.lower()) for term in [
            "ماذا تستطيع",
            "what can you do",
        ]]):
            reply = "أنا أمير، شريكك التنفيذي. أفهم هدفك، أحدد المسار، أنسّق ما يلزم، وأقدم الرد النهائي باسمي."
            facts = {
                "subject": "ameer",
                "name": "Ameer",
                "role": "Executive Partner",
                "purpose": "Executive planning, coordination, and final response ownership",
            }
        elif any(term in qn for term in [self.normalize_fn(term.lower()) for term in [
            "حدود",
            "limits",
            "كيف تعمل",
            "how do you work",
        ]]):
            reply = "أعمل كشريك تنفيذي تحت سلطة المؤسس. أستطيع التحليل والتخطيط والتنسيق، والقرارات المصيرية تبقى معك."
            facts = {
                "subject": "ameer",
                "name": "Ameer",
                "role": "Executive Partner",
                "purpose": "Constitution-bound executive reasoning",
            }
        else:
            reply = "أنا أمير، شريكك التنفيذي. أتفاعل معك مباشرة وأقرر متى أجيب بنفسي ومتى أستعين بما يلزم ثم أقدم الرد النهائي باسمي."
            facts = {
                "subject": "ameer",
                "name": "Ameer",
                "role": "Executive Partner",
                "purpose": "Executive reasoning and final response ownership",
            }

        return AgentOutput(
            agent="ameer_core",
            confidence=0.96,
            reply_draft=reply,
            sources=CORE_ROUTE_CAPABILITIES["ameer_core"]["primary_sources"],
            actions=["answer_core_identity"],
            message="تمت الإجابة من Ameer Core.",
            response_data={
                "intent": "identity",
                "facts": facts,
            },
        )

    def classify_intent(self, query: str) -> str:
        return self.route_query(query)["intent"]

    def _infer_semantic_intent(self, query: str) -> Dict[str, str | float] | None:
        q = f" {self.normalize_fn(query.lower())} "

        explicit_onboarding_markers = [
            " أريد أن أخبرك عني ",
            " اريد ان اخبرك عني ",
            " سأخبرك عني ",
            " ساخبرك عني ",
            " أريد أن أشاركك عني ",
            " اريد ان اشاركك عني ",
            " أحب أن تتذكر ",
            " احب ان تتذكر ",
            " أريد أن تتذكر ",
            " اريد ان تتذكر ",
            " أريد أن تحفظ ",
            " اريد ان تحفظ ",
            " هذه معلومة عني ",
            " هذه معلومه عني ",
            " معلومة عني ",
            " معلومه عني ",
            " tell you about me ",
            " tell you about myself ",
            " for your memory ",
            " remember that i ",
            " remember that i am ",
            " save this about me ",
            " save this about myself ",
            " احفظ انني ",
            " احفظ ان ",
            " تذكر انني ",
            " تذكر ان ",
            " تذكر أنني ",
            " تذكر أن ",
        ]
        explicit_onboarding_markers = [self.normalize_fn(marker.lower()) for marker in explicit_onboarding_markers]
        if any(marker in q for marker in explicit_onboarding_markers):
            return {
                "intent": "onboarding",
                "reason": "semantic inference detected user-provided memory or onboarding input",
                "confidence": 0.88,
            }

        has_memory_write = any(term in q for term in [" احفظ ", " تذكر ", " remember ", " save ", " تتذكر ", " تحفظ "])
        has_personal_fact = any(term in q for term in [" انا ", " انني ", " عندي ", " أفضل ", " افضل ", " i ", " my ", " me ", " myself "])
        has_self_reference = any(term in q for term in [" عني ", " عني ", " myself ", " me ", " my "])
        if has_memory_write and (has_personal_fact or has_self_reference):
            return {
                "intent": "onboarding",
                "reason": "semantic inference detected a first-person fact intended for memory",
                "confidence": 0.84,
            }

        return None

    def _extract_onboarding_fact(self, query: str) -> str | None:
        q = query.strip()
        if not q:
            return None

        patterns = [
            r"(?:أحب\s+أن\s+تتذكر|أريد\s+أن\s+تتذكر|أريد\s+أن\s+تحفظ|أحب\s+أن\s+تحفظ|تذكر\s+أنني|تذكر\s+أن|احفظ\s+أنني|احفظ\s+أن)\s*(.+)",
            r"(?:أنني|انني|أني|أنا)\s+(.+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, q, flags=re.IGNORECASE | re.UNICODE)
            if match:
                fact = match.group(1).strip(" .،؟")
                if fact and len(fact) > 2:
                    return fact
        return None

    def _is_execution_request(self, query: str) -> bool:
        q = self.normalize_fn(query.lower())
        file_terms = [
            "file",
            "ملف",
            "ملفا",
            "folder",
            "مجلد",
            "directory",
            "دليل",
            "page",
            "صفحة",
            "script",
            "سكريبت",
            "code",
            "كود",
            "project",
            "مشروع",
            "website",
            "موقع",
        ]
        execution_patterns = [
            "أنشئ ملف",
            "أنشئ ملفًا",
            "أنشأ ملف",
            "إنشاء ملف",
            "اكتب ملف",
            "انشئ ملف",
            "انشي ملف",
            "انشي ملفا",
            "انشئ ملفا",
            "انشأ ملف",
            "create file",
            "make file",
            "new file",
            "write file",
            "create folder",
            "make folder",
            "create directory",
            "make directory",
            "create page",
            "create script",
            "write script",
            "أنشئ مجلد",
            "أنشئ دليل",
            "إنشاء مجلد",
            "إنشاء دليل",
            "أنشئ صفحة",
            "ابن ملف",
            "build file",
            "أنشئ مشروع",
            "إنشاء مشروع",
            "أنشئ موقع",
            "إنشاء موقع",
            "create project",
            "build project",
            "create website",
            "build website",
        ]
        if any(pattern in q for pattern in execution_patterns):
            return True
        return any(term in q for term in file_terms) and any(
            verb in q for verb in ["أنشئ", "أنشأ", "إنشاء", "create", "make", "write", "build", "add", "اكتب", "ابن", "انشئ", "انشي", "ابدأ", "start"]
        )

    def _is_project_creation_request(self, query: str) -> bool:
        q = self.normalize_fn(query.lower())
        project_patterns = [
            "ابن موقع",
            "أنشئ موقع",
            "إنشاء موقع",
            "بناء موقع",
            "create website",
            "build website",
            "new website",
            "new project",
            "create project",
            "build project",
            "start project",
            "launch project",
            "open project",
            "ابدأ مشروع",
            "افتتاح مشروع",
            "أنشئ مشروع",
            "إنشاء مشروع",
            "أنشئ تطبيق",
            "إنشاء تطبيق",
            "create app",
            "build app",
            "new app",
        ]
        return any(pattern in q for pattern in project_patterns)

    def _persist_onboarding_memory(self, query: str, intent: str) -> Dict[str, object]:
        if intent != "onboarding":
            return {"saved": False, "file": None, "fact": None, "reason": "intent_not_onboarding"}

        fact = self._extract_onboarding_fact(query)
        if not fact:
            return {"saved": False, "file": None, "fact": None, "reason": "no_fact_extracted"}

        workspace_root = os.path.abspath(os.path.join(CODE_ROOT, ".."))
        pending_file = os.path.join(workspace_root, ".ameer", "onboarding_candidates.json")
        os.makedirs(os.path.dirname(pending_file), exist_ok=True)
        candidates: List[Dict[str, object]] = []
        if os.path.exists(pending_file):
            try:
                with open(pending_file, "r", encoding="utf-8") as handle:
                    loaded = json.load(handle)
                    if isinstance(loaded, list):
                        candidates = loaded
            except Exception:
                candidates = []

        candidate = {
            "id": str(uuid.uuid4()),
            "fact": fact,
            "source": "onboarding_query",
            "timestamp": _now_iso(),
            "confidence": 0.7,
            "approval_state": "pending",
            "target_layer": "founder_memory",
            "reason": "onboarding_requires_explicit_approval",
        }
        candidates.append(candidate)
        with open(pending_file, "w", encoding="utf-8") as handle:
            json.dump(candidates[-300:], handle, ensure_ascii=False, indent=2)

        return {
            "saved": False,
            "file": ".ameer/onboarding_candidates.json",
            "fact": fact,
            "reason": "pending_approval",
            "approval_state": "pending",
            "candidate_id": candidate["id"],
        }

    def route_query(self, query: str) -> Dict[str, str | bool | float | List[str]]:
        q = self.normalize_fn(query.lower())

        semantic_route = self._infer_semantic_intent(query)
        if semantic_route is not None:
            intent = str(semantic_route["intent"])
            agent = ROUTE_AGENT_MAP.get(intent, "research_agent")
            capabilities = self._capabilities_for_executor(agent)
            return {
                "intent": intent,
                "agent": agent,
                "confidence": float(semantic_route["confidence"]),
                "reason": str(semantic_route["reason"]),
                "identity_layer": False,
                "agent_capabilities": capabilities,
            }

        # Detect messages that are ONLY the assistant's name (a name-call, not a search query)
        assistant_name_forms = ["أمير", "امير", "ameer"]
        q_words_only = re.sub(r"[^\u0621-\u064Aa-zA-Z0-9]", "", q).strip()
        if q_words_only in [self.normalize_fn(n.lower()) for n in assistant_name_forms]:
            agent = ROUTE_AGENT_MAP.get("greeting", "greeting_agent")
            capabilities = self._capabilities_for_executor(agent)
            return {
                "intent": "greeting",
                "agent": agent,
                "confidence": 0.99,
                "reason": "matched assistant name call — treating as a call to the assistant, not a search",
                "identity_layer": False,
                "agent_capabilities": capabilities,
            }

        greeting_terms = ["مرحبا", "اهلا", "أهلا", "السلام عليكم", "هلا", "hello", "hi", "hey"]
        identity_terms = [
            "من هي نسيم",
            "من هو نسيم",
            "who is naseem",
            "من انا",
            "من أنا",
            "من هو صاحب المشروع",
            "من هي صاحبة المشروع",
            "عرفني بنفسي",
            "المؤسس",
            "founder",
            "naseem",
            "نسيم",
        ]
        project_terms = [
            "ما هو هدف المشروع",
            "هدف المشروع",
            "رؤية امير",
            "رؤية أمير",
            "vision",
            "master plan",
            "ملفات المشروع",
            "project",
            "مشروع",
        ]
        memory_terms = ["ذاكره", "ذاكرة", "memory", "تذكر", "remember", "احفظ", "recall", "save"]
        memory_retrieval_terms = ["كلمة السر", "كلمة المرور", "secret", "password", "ما الذي حفظت", "ما حفظت", "ما الذي تذكرته", "ما تذكرته", "معلومة", "الذاكرة"]

        reason = "default knowledge lookup"
        confidence = 0.55

        if self._is_project_creation_request(query):
            intent = "project"
            reason = "matched project creation request"
            confidence = 0.95
        elif self._is_execution_request(query):
            intent = "execution"
            reason = "matched execution request"
            confidence = 0.98
        elif any(term in q for term in [self.normalize_fn(t.lower()) for t in memory_retrieval_terms]):
            intent = "memory"
            reason = "matched memory retrieval keyword"
            confidence = 0.92
        elif any(term in q for term in [self.normalize_fn(t.lower()) for t in memory_terms]):
            intent = "memory"
            reason = "matched memory keyword"
            confidence = 0.9
        elif any(term in q for term in [self.normalize_fn(t.lower()) for t in greeting_terms]):
            intent = "greeting"
            reason = "matched greeting keyword"
            confidence = 0.97
        elif self._is_identity_question(query) or any(term in q for term in [self.normalize_fn(t.lower()) for t in identity_terms]):
            intent = "identity"
            reason = "matched identity pattern or founder identity term"
            confidence = 0.94
        elif any(term in q for term in [self.normalize_fn(t.lower()) for t in project_terms]):
            intent = "project"
            reason = "matched project intent keyword"
            confidence = 0.9
        else:
            intent = "knowledge_lookup"

        agent = ROUTE_AGENT_MAP.get(intent, "research_agent")
        capabilities = self._capabilities_for_executor(agent)

        return {
            "intent": intent,
            "agent": agent,
            "confidence": confidence,
            "reason": reason,
            "identity_layer": intent == "identity",
            "agent_capabilities": capabilities,
        }

    def _normalize_path(self, path: str) -> str:
        return path.replace("\\", "/").lower()

    def _match_any_pattern(self, path: str, patterns: List[str]) -> bool:
        p = self._normalize_path(path)
        for raw in patterns:
            pat = raw.lower()
            if pat.endswith("/"):
                if p.startswith(pat):
                    return True
            elif p == pat or p.endswith("/" + pat):
                return True
        return False

    def _get_policy(self, route: str) -> SourcePolicy | None:
        for policy in self.policies:
            if policy.route == route:
                return policy
        return None

    def _extract_project_name(self, query: str) -> str | None:
        q = query.strip()
        quoted = re.search(r"[\"']([^\"']+)[\"']", q)
        if quoted:
            return quoted.group(1).strip().lower()

        m = re.search(r"(?:project|مشروع)\s+([\w\-_/]+)", q, flags=re.IGNORECASE)
        if m:
            return m.group(1).strip().lower()
        return None

    def guardian_check(self, query: str, intent: str) -> Dict:
        q = self.normalize_fn(query.lower())
        has_risky_action = any(term in q for term in self.high_risk_action_terms)
        has_explicit_approval = any(term in q for term in self.explicit_approval_terms)
        has_founder_identity = any(term in q for term in self.founder_identity_terms)

        # Approval token can be passed inline as a policy signal for actionable tasks.
        # Examples: "approved by founder", "موافقة المؤسس", "founder approved".
        approval_token = has_explicit_approval and has_founder_identity

        if has_risky_action and approval_token:
            return {
                "status": "pass",
                "risk_level": "medium",
                "mode": "execution_ready",
                "reason": "تم رصد موافقة صريحة من المؤسس، ويمكن متابعة التنفيذ مع الحذر.",
                "approval_token": "founder_explicit_approval",
            }

        if has_risky_action and not approval_token:
            return {
                "status": "needs_approval",
                "risk_level": "high",
                "mode": "read_only",
                "reason": "تم اكتشاف طلب تنفيذي/حساس بدون موافقة صريحة من المؤسس.",
                "approval_token": None,
            }

        if intent in ["identity", "memory", "project", "investment", "execution", "migration", "guidance"]:
            return {
                "status": "pass",
                "risk_level": "low",
                "mode": "analysis",
                "reason": "السؤال ضمن نطاق التحليل والقراءة وفق سياسات الدستور.",
                "approval_token": None,
            }

        return {
            "status": "pass",
            "risk_level": "low",
            "mode": "analysis",
            "reason": "لا توجد مؤشرات خطر مباشرة في الطلب.",
            "approval_token": None,
        }

    def _excerpt(self, query: str, text: str) -> str:
        q_first_word = query.split()[0] if query.split() else query
        q_first_word_norm = self.normalize_fn(q_first_word)
        pattern = re.compile(
            r"(.{0," + str(self.config.window_chars) + r"}" + re.escape(q_first_word) + r".{0," + str(self.config.window_chars) + r"})",
            re.IGNORECASE,
        )
        m = pattern.search(text) if q_first_word else None
        if m:
            return m.group(1).strip()

        if q_first_word_norm:
            norm_text = self.normalize_fn(text)
            idx = norm_text.lower().find(q_first_word_norm.lower())
            if idx >= 0:
                start = max(0, idx - self.config.window_chars)
                end = min(len(text), idx + self.config.window_chars)
                return text[start:end].strip()

        return text[: self.config.max_excerpt_chars].strip()

    def retrieve(self, query: str, route: str, max_results: int) -> List[Dict[str, str | int]]:
        if route == "project":
            return self._retrieve_project(query, max_results)

        policy = self._get_policy(route)
        if policy is None:
            return self._retrieve_by_similarity(query, self.documents, max_results)

        ordered: List[Dict[str, str | int]] = []
        remaining = max_results

        for group_index, group_patterns in enumerate(policy.priority_groups):
            group_docs = [d for d in self.documents if self._match_any_pattern(d["path"], group_patterns)]
            if not group_docs:
                continue

            group_results = self._retrieve_by_similarity(query, group_docs, max_results)

            if group_results:
                take = group_results[:remaining]
                ordered.extend(take)
                remaining = max_results - len(ordered)
            elif group_index == 0 and policy.force_first_group and remaining > 0:
                d0 = group_docs[0]
                ordered.append(
                    {
                        "path": d0["path"],
                        "score": 0,
                        "excerpt": d0["text"][: self.config.max_excerpt_chars].strip(),
                    }
                )
                remaining = max_results - len(ordered)

            if remaining <= 0:
                break

        return ordered[:max_results]

    def _retrieve_project(self, query: str, max_results: int) -> List[Dict[str, str | int]]:
        policy = self._get_policy("project")
        if policy is None:
            return self._retrieve_by_similarity(query, self.documents, max_results)

        project_name = self._extract_project_name(query)
        ordered: List[Dict[str, str | int]] = []
        remaining = max_results

        # 1) Always read Master Plan first.
        master_plan_docs = [d for d in self.documents if self._match_any_pattern(d["path"], policy.priority_groups[0])]
        if master_plan_docs:
            first_group_results = self._retrieve_by_similarity(query, master_plan_docs, max_results)
            if first_group_results:
                ordered.extend(first_group_results[:remaining])
            else:
                ordered.append(
                    {
                        "path": master_plan_docs[0]["path"],
                        "score": 0,
                        "excerpt": master_plan_docs[0]["text"][: self.config.max_excerpt_chars].strip(),
                    }
                )
            remaining = max_results - len(ordered)

        if remaining <= 0:
            return ordered[:max_results]

        # 2) Then read project-specific files if project is resolved.
        if project_name:
            project_docs = [
                d for d in self.documents if project_name in self._normalize_path(d["path"]) and not self._match_any_pattern(d["path"], policy.priority_groups[0])
            ]
            if project_docs:
                second_group_results = self._retrieve_by_similarity(query, project_docs, max_results)
                ordered.extend(second_group_results[:remaining])
                remaining = max_results - len(ordered)

        # 3) Fallback to generic project context sources.
        if remaining > 0:
            fallback_docs = [d for d in self.documents if self._match_any_pattern(d["path"], policy.priority_groups[1])]
            fallback_results = self._retrieve_by_similarity(query, fallback_docs, max_results)
            ordered.extend(fallback_results[:remaining])

        dedup: List[Dict[str, str | int]] = []
        seen = set()
        for item in ordered:
            path = str(item["path"])
            if path in seen:
                continue
            seen.add(path)
            dedup.append(item)
        return dedup[:max_results]

    def _retrieve_by_similarity(
        self,
        query: str,
        docs: List[Dict[str, str]],
        max_results: int,
    ) -> List[Dict[str, str | int]]:
        results: List[Dict[str, str | int]] = []
        for doc in docs:
            score = self.score_fn(query, doc["text"])
            if score > 0:
                results.append(
                    {
                        "path": doc["path"],
                        "score": score,
                        "excerpt": self._excerpt(query, doc["text"]),
                    }
                )

        results.sort(key=lambda x: int(x["score"]), reverse=True)
        return results[:max_results]

    def _intent_message(self, intent: str) -> str:
        if intent == "identity":
            return "سأتعامل مع سؤالك كموضوع هوية، وسأقرأ Constitution أولًا كمرجع وحيد أساسي."
        if intent == "memory":
            return "سأتعامل مع سؤالك كموضوع ذاكرة، وسأقرأ ملفات Memory حسب الأولوية."
        if intent == "project":
            return "سأبدأ بـ Master Plan ثم ملفات المشروع بالترتيب قبل صياغة الإجابة."
        if intent == "investment":
            return "سأبدأ بـ Finance ثم Investment ثم أكمل حسب ترتيب الأولوية."
        if intent == "execution":
            return "سأقرأ Architecture أولًا ثم Code قبل تقديم أي توجيه تنفيذي."
        if intent == "migration":
            return "سأتعامل مع سؤالك كموضوع نقل الهوية والذاكرة ثم أبحث في الوثائق."
        if intent == "guidance":
            return "سأقدّم توجيهًا عمليًا مدعومًا بما يوجد في مستندات المشروع."
        return "سأبحث في معرفة المشروع وأركب إجابة موجزة."

    def _source_order_for_intent(self, intent: str, query: str) -> List[List[str]]:
        policy = self._get_policy(intent)
        if not policy:
            return []
        if intent == "project":
            project_name = self._extract_project_name(query)
            if project_name:
                return [
                    ["01_docs/master_plan.md"],
                    [f"*{project_name}* (project-specific files)"],
                    policy.priority_groups[1],
                ]
        return policy.priority_groups

    def _get_session_state(self, session_id: str | None) -> Dict:
        if not session_id:
            return {"has_context": False, "active_goal": None, "last_query": None, "turns": 0}
        if session_id not in self.session_memory:
            self.session_memory[session_id] = {
                "has_context": False,
                "active_goal": None,
                "last_query": None,
                "turns": 0,
                "history": [],
            }
        return self.session_memory[session_id]

    def _update_session_state(self, session_id: str | None, query: str, intent: str, reply: str, conversation_state: Dict) -> None:
        if not session_id:
            return
        state = self.session_memory.setdefault(session_id, {
            "has_context": False,
            "active_goal": None,
            "last_query": None,
            "turns": 0,
            "history": [],
        })
        state["last_query"] = query
        state["turns"] = state.get("turns", 0) + 1
        state["history"].append({"query": query, "intent": intent, "reply": reply})
        if conversation_state.get("active_goal"):
            state["active_goal"] = conversation_state["active_goal"]
        state["has_context"] = bool(state.get("active_goal") or state.get("history"))

    def _detect_follow_up(self, query: str, state: Dict) -> bool:
        q = self.normalize_fn(query.lower())
        follow_up_terms = ["أول خطوة", "الخطوة", "ماذا بعد", "ما أول", "التالي", "ثم", "تغيرت", "غيرت رأيي", "هل تغيرت", "غيرت", "الهدف"]
        return bool(state.get("has_context") and any(term in q for term in follow_up_terms))

    def _infer_active_goal(self, query: str, state: Dict, intent: str) -> tuple[str | None, bool]:
        q = self.normalize_fn(query.lower())
        extracted = None
        if "مشروع" in q or "project" in q:
            if "افتتاح" in q or "open" in q or "بدء" in q:
                extracted = "افتتاح مشروع جديد"
            elif "اشتري" in q or "شراء" in q or "company" in q or "شركة" in q:
                extracted = "شراء شركة جاهزة"
        elif "شركة" in q or "company" in q:
            extracted = "شراء شركة جاهزة"
        elif "افتتاح" in q or "فتح" in q or "open" in q:
            extracted = "افتتاح مشروع جديد"
        elif "أول خطوة" in q or "الخطوة" in q or "ما أول" in q or "ماذا بعد" in q:
            extracted = state.get("active_goal")

        if not extracted and state.get("active_goal"):
            return state.get("active_goal"), False

        if not extracted:
            return None, False

        if state.get("active_goal") and extracted != state.get("active_goal"):
            return extracted, True
        return extracted, False

    def _build_execution_plan(self, query: str, intent: str, results: List[Dict]) -> Dict:
        q = self.normalize_fn(query.lower())
        if intent == "identity":
            return {
                "planner": "identity_layer",
                "goal": "توضيح هوية أمير بشكل واضح ومختصر.",
                "steps": ["تحديد نوع السؤال", "اختيار الرد التعريفي المناسب", "تقديم إجابة مباشرة"],
                "reviewer_note": "تأكد من أن الإجابة تعكس الهوية الأساسية دون الخروج عن الدستور.",
            }

        goal = "إجابة مفيدة مبنية على الوثائق المتاحة."
        steps = ["تحديد الهدف من السؤال", "استرجاع الوثائق ذات الصلة", "تلخيص المعلومات في إجابة واضحة"]
        if results:
            steps.append("مراجعة المقتطفات قبل الصياغة")
        else:
            steps.append("الإبلاغ عن عدم وجود معلومات كافية")

        if any(term in q for term in ["كيف", "خطة", "خطوات", "ابدأ", "أبدأ", "project", "مشروع", "plan"]):
            goal = "وضع خطة عملية أو توجيه واضح بناءً على السؤال."
            steps = ["فهم الهدف", "ربط السؤال بالأدلة المتاحة", "صياغة خطة أو توجيه عملي"]

        return {
            "planner": "planning_layer",
            "goal": goal,
            "steps": steps,
            "reviewer_note": "راجع أن الإجابة لا تخرج عن المستندات وتكون واضحة ومحددة.",
        }

    def answer(self, query: str, max_results: int = 5, session_id: str | None = None) -> Dict:
        route = self.route_query(query)
        intent = str(route["intent"])
        memory_update = self._persist_onboarding_memory(query, intent)
        guardian = self.guardian_check(query, intent)
        state = self._get_session_state(session_id)
        follow_up = self._detect_follow_up(query, state)
        active_goal, plan_shifted = self._infer_active_goal(query, state, intent)
        conversation_state = {
            "has_context": bool(active_goal or state.get("history")) or follow_up or intent in ["identity", "project", "memory"],
            "active_goal": active_goal,
            "is_follow_up": follow_up,
            "plan_shifted": plan_shifted,
            "turns": state.get("turns", 0) + 1,
        }

        is_identity = bool(route["identity_layer"])
        results = [] if intent == "greeting" else self.retrieve(query, intent, max_results)
        project_name = self._extract_project_name(query) if intent == "project" else None
        execution_plan = self._build_execution_plan(query, intent, results)

        selected_agent = str(route.get("agent", "research_agent"))
        recovery_used = False
        recovery_reason = None
        context = AgentContext(
            query=query,
            intent=intent,
            route=route,
            results=results,
            execution_plan=execution_plan,
            conversation_state=conversation_state,
            active_goal=active_goal,
        )

        if selected_agent == "ameer_core":
            agent_output = self._build_core_identity_payload(query)
        else:
            agent = self.agents.get(selected_agent, self.agents["research_agent"])
            try:
                agent_output = agent.execute(context)
            except Exception as exc:
                recovery_used = True
                recovery_reason = f"agent_execute_failure:{exc}"
                agent_output = self.agents["recovery_agent"].execute(context)

        output_validation = self._validate_agent_output(agent_output)

        if not output_validation["ok"]:
            recovery_used = True
            if recovery_reason is None:
                recovery_reason = "agent_contract_validation_failure"
            agent_output = self.agents["recovery_agent"].execute(context)
            output_validation = self._validate_agent_output(agent_output)

        if output_validation["ok"]:
            try:
                brain_payload = self.agent_brain_adapter.prepare(agent_output)
            except Exception as exc:
                recovery_used = True
                recovery_reason = f"adapter_prepare_failure:{exc}"
                recovery_output = self.agents["recovery_agent"].execute(context)
                brain_payload = self.agent_brain_adapter.prepare(recovery_output)

            draft_reply = str(brain_payload.get("draft", "")).strip()
            message = str(brain_payload.get("message", "")).strip()
            selected_agent_name = str(brain_payload.get("agent", selected_agent))
            confidence = float(brain_payload.get("confidence", 0.0))
            sources = list(brain_payload.get("sources", []))
            actions = list(brain_payload.get("actions", []))
            response_data = brain_payload.get("response_data", {})
            if not isinstance(response_data, dict):
                response_data = {}
        else:
            draft_reply = "لا توجد نتائج كافية، يلزم توليد رد توضيحي من Executive Brain."
            message = (
                "تم إيقاف التسليم من الوكيل بسبب كسر عقد البيانات. "
                "يجب تحديث الوكيل ليرجع AgentOutput كامل الحقول."
            )
            selected_agent_name = selected_agent
            confidence = 0.0
            sources = []
            actions = []
            response_data = {}
            brain_payload = {
                "agent": selected_agent_name,
                "confidence": confidence,
                "draft": draft_reply,
                "sources": sources,
                "actions": actions,
                "message": message,
                "response_data": response_data,
            }

        agent_result = {
            "agent": selected_agent_name,
            "confidence": confidence,
            "reply_draft": draft_reply,
            "sources": sources,
            "actions": actions,
            "response_data": response_data,
        }

        response = {
            "query": query,
            "intent": intent,
            "reasoning_layer": "active",
            "orchestrator": {
                "version": "v1",
                "step": [
                    "router",
                    "intent_classification",
                    "guardian_check",
                    "source_policy_routing",
                    "document_retrieval",
                    "coordination_synthesis",
                    "register",
                    "select",
                    "execute",
                    "validate",
                    "send_to_executive_brain",
                ],
                "agent_lifecycle": [
                    "REGISTER",
                    "SELECT",
                    "EXECUTE",
                    "VALIDATE",
                    "SEND_TO_EXECUTIVE_BRAIN",
                ],
                "decision": self._intent_message(intent),
                "source_order": self._source_order_for_intent(intent, query),
                "resolved_project": project_name,
                "trace": [
                    {"step": "router", "output": route},
                    {"step": "intent_classification", "output": intent},
                    {"step": "guardian_check", "output": guardian["status"]},
                    {"step": "source_policy_routing", "output": self._source_order_for_intent(intent, query)},
                    {"step": "document_retrieval", "output": len(results)},
                    {"step": "register", "output": {"registry_size": len(self.agents)}},
                    {"step": "select", "output": selected_agent},
                    {"step": "execute", "output": "core_direct" if selected_agent == "ameer_core" else "ok"},
                    {"step": "validate", "output": output_validation},
                    {"step": "send_to_executive_brain", "output": "ready"},
                ],
            },
            "routing": route,
            "guardian": guardian,
            "reply": draft_reply,
            "draft_reply": draft_reply,
            "reply_owner": "executive_brain_pending",
            "memory_update": memory_update,
            "message": message,
            "selected_agent": selected_agent_name,
            "agent_result": agent_result,
            "agent_brain_payload": brain_payload,
            "fallback": {
                "used": recovery_used,
                "reason": recovery_reason,
                "recovery_agent": "recovery_agent" if recovery_used else None,
            },
            "execution_plan": execution_plan,
            "results": results,
            "count": len(results),
            "identity_layer": {"active": is_identity, "source": "core_identity" if is_identity else "none"},
        }
        response["conversation_state"] = conversation_state
        self._update_session_state(session_id, query, intent, draft_reply, conversation_state)
        response["session_id"] = session_id
        return response
