from __future__ import annotations

import json
import re
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class ConversationPlannerState:
    executive_objective: str = ""
    founder_objective: str = ""
    current_project_objective: str = ""
    detected_risks: List[str] | None = None
    missing_information: List[str] | None = None
    next_executive_action: str = ""

    def to_dict(self) -> dict:
        data = asdict(self)
        data["detected_risks"] = list(self.detected_risks or [])
        data["missing_information"] = list(self.missing_information or [])
        return data


class PersistentConversationMemory:
    def __init__(self, workspace_root: str | Path) -> None:
        self._root = Path(workspace_root).resolve()
        self._path = self._root / ".ameer" / "conversation_memory.json"
        self._state: Dict[str, Any] = self._load()

    def _default_state(self) -> dict:
        return {
            "unfinished_discussions": [],
            "previous_promises": [],
            "pending_questions": [],
            "user_priorities": [],
            "ongoing_projects": [],
            "recurring_topics": [],
            "relationship_continuity": {"last_summary": "", "last_reply": "", "last_user_message": ""},
            "executive_commitments": [],
            "initiative_log": [],
            "last_planner_state": {},
            "updated_at": _now_iso(),
            "created_at": _now_iso(),
        }

    def _load(self) -> dict:
        if self._path.exists():
            try:
                data = json.loads(self._path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    return data
            except Exception:
                pass
        state = self._default_state()
        self._persist(state)
        return state

    def _persist(self, state: Optional[dict] = None) -> None:
        if state is not None:
            self._state = state
        self._state["updated_at"] = _now_iso()
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(self._state, ensure_ascii=False, indent=2), encoding="utf-8")

    def snapshot(self) -> dict:
        return dict(self._state)

    def build_context_block(self) -> str:
        parts: List[str] = []
        if self._state.get("unfinished_discussions"):
            parts.append("نقاط مفتوحة: " + " | ".join(self._state["unfinished_discussions"][:3]))
        if self._state.get("pending_questions"):
            parts.append("أسئلة بانتظار الحسم: " + " | ".join(self._state["pending_questions"][:3]))
        if self._state.get("executive_commitments"):
            parts.append("التزامات تنفيذية: " + " | ".join(self._state["executive_commitments"][:3]))
        if self._state.get("recurring_topics"):
            parts.append("مواضيع متكررة: " + " | ".join(self._state["recurring_topics"][:3]))
        return "[ ذاكرة الشراكة:\n" + "\n".join(parts) + "\n]" if parts else ""

    def plan(
        self,
        query: str,
        *,
        active_projects: Optional[List[str]] = None,
        running_tasks: Optional[List[dict]] = None,
        pending_approvals: Optional[List[dict]] = None,
        workspace_summary: str = "",
        executive_assessment: str = "",
    ) -> ConversationPlannerState:
        q = (query or "").strip()
        risks: List[str] = []
        missing: List[str] = []
        current_project = active_projects[0] if active_projects else ""

        if pending_approvals:
            risks.append("هناك موافقات معلقة قد تؤخر التنفيذ")
        if running_tasks:
            stalled = [t for t in running_tasks if str(t.get("status", "")).lower() in {"pending", "blocked"}]
            if stalled:
                risks.append("توجد مهام مفتوحة تحتاج حسمًا قبل التوسع")
        if "fail" in workspace_summary.lower() or "error" in workspace_summary.lower():
            risks.append("بيئة العمل تحمل مؤشرات فشل تحتاج مراجعة")
        if len(q) < 4:
            missing.append("الطلب الحالي مختصر أكثر من اللازم ويحتاج تحديدًا")

        founder_objective = q or "استمرار التقدم في العمل الجاري"
        executive_objective = executive_assessment or founder_objective
        next_action = "أغلق نقطة القرار التالية ثم واصل التنفيذ."
        if pending_approvals:
            next_action = "احسمي طلب الموافقة المعلق أولًا حتى لا يتعطل المسار التالي."
        elif running_tasks:
            next_action = "لنغلق المهمة المفتوحة الأعلى أثرًا قبل فتح مسار جديد."

        return ConversationPlannerState(
            executive_objective=executive_objective,
            founder_objective=founder_objective,
            current_project_objective=current_project or founder_objective,
            detected_risks=risks,
            missing_information=missing,
            next_executive_action=next_action,
        )

    def update_after_reply(self, query: str, reply: str, planner_state: ConversationPlannerState) -> None:
        q = (query or "").strip()
        r = (reply or "").strip()
        if q:
            self._remember_topic(q)
            if q.endswith("؟") or "?" in q:
                self._upsert_list("pending_questions", q, remove_if_answered=bool(r))
            else:
                self._upsert_list("unfinished_discussions", q)
        if planner_state.next_executive_action:
            self._upsert_list("executive_commitments", planner_state.next_executive_action)
        if "سأ" in r or "سوف" in r:
            self._upsert_list("previous_promises", r[:180])
        self._state["relationship_continuity"] = {
            "last_summary": planner_state.executive_objective,
            "last_reply": r[:260],
            "last_user_message": q[:260],
        }
        self._state["last_planner_state"] = planner_state.to_dict()
        self._persist()

    def record_initiative(self, trigger: str, detail: str) -> None:
        log = self._state.setdefault("initiative_log", [])
        log.insert(0, {"trigger": trigger, "detail": detail, "at": _now_iso()})
        self._state["initiative_log"] = log[:20]
        self._persist()

    def _remember_topic(self, text: str) -> None:
        normalized = re.sub(r"\s+", " ", text).strip()
        if normalized:
            self._upsert_list("recurring_topics", normalized[:120])

    def _upsert_list(self, key: str, value: str, remove_if_answered: bool = False) -> None:
        items = [str(v) for v in self._state.get(key, []) if str(v).strip()]
        if remove_if_answered and value in items:
            items = [item for item in items if item != value]
        elif value not in items:
            items.insert(0, value)
        self._state[key] = items[:10]


class ExecutiveConversationEngine:
    def __init__(self, workspace_root: str | Path) -> None:
        self.memory = PersistentConversationMemory(workspace_root)

    def execute(
        self,
        *,
        query: str,
        draft_reply: str,
        planner_state: ConversationPlannerState,
        conversation_context: str = "",
        persistent_memory_block: str = "",
        pending_approvals: Optional[List[dict]] = None,
        running_tasks: Optional[List[dict]] = None,
        active_projects: Optional[List[str]] = None,
        is_first_turn: bool = False,
    ) -> dict:
        reply = self._enforce_style(draft_reply, planner_state)
        initiative = self._build_initiative(
            pending_approvals=pending_approvals,
            running_tasks=running_tasks,
            active_projects=active_projects,
            is_first_turn=is_first_turn,
        )
        if initiative:
            reply = f"{initiative} {reply}".strip()
        self.memory.update_after_reply(query, reply, planner_state)
        return {
            "reply": reply,
            "planner_state": planner_state.to_dict(),
            "initiative": initiative,
            "engine": "executive_conversation_engine",
            "memory_context_used": bool(conversation_context or persistent_memory_block),
        }

    def _build_initiative(
        self,
        *,
        pending_approvals: Optional[List[dict]],
        running_tasks: Optional[List[dict]],
        active_projects: Optional[List[str]],
        is_first_turn: bool,
    ) -> str:
        if pending_approvals:
            detail = str(pending_approvals[0].get("description") or pending_approvals[0].get("summary") or "قرار معلق")
            self.memory.record_initiative("pending_approval", detail)
            return f"راجعت الحالة قبل الرد، ويوجد طلب موافقة معلّق: {detail}."
        if is_first_turn and running_tasks:
            self.memory.record_initiative("unfinished_conversation", "running_tasks")
            return "راجعت ما استمر مفتوحًا منذ آخر جلسة، وهناك مسار تنفيذي يحتاج إغلاقًا قبل التوسع."
        if is_first_turn and active_projects:
            self.memory.record_initiative("project_continuity", active_projects[0])
            return f"أتعامل مع هذه الجلسة كامتداد مباشر للعمل على {active_projects[0]}."
        return ""

    def _enforce_style(self, reply: str, planner_state: ConversationPlannerState) -> str:
        text = (reply or "").strip()
        replacements = {
            "كيف أستطيع مساعدتك؟": "حددي القرار أو المسار الذي تريدين حسمه الآن.",
            "كيف أساعدك؟": "حددي النقطة التي نحتاج حسمها الآن.",
            "هل تحتاج شيئًا آخر؟": planner_state.next_executive_action,
            "يسعدني مساعدتك": "سأركز معك على ما يغيّر النتيجة",
            "مرحبا": "أتابع معك",
            "مرحبًا": "أتابع معك",
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        text = re.sub(r"\bforward\b", "إلى الأمام", text, flags=re.IGNORECASE)
        text = re.sub(r"\s{2,}", " ", text).strip()

        if planner_state.detected_risks:
            risk_line = "المخاطر الحالية: " + "، ".join(planner_state.detected_risks[:2]) + "."
            if risk_line not in text:
                text = f"{risk_line} {text}".strip()

        if planner_state.missing_information:
            question = planner_state.missing_information[0]
            if "؟" not in text:
                text = f"{text} ما أحتاجه الآن: {question}."

        if planner_state.next_executive_action and planner_state.next_executive_action not in text:
            text = f"{text} الخطوة التالية: {planner_state.next_executive_action}"

        return text
