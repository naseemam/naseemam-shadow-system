from __future__ import annotations

import json
import logging
import re
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _root_asset_creation_requested(query: str) -> bool:
    """Return whether a natural-language command opens one of four root assets."""
    text = (query or "").lower()
    normalized = text.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").replace("ى", "ي")
    markers = (
        "موقع جديد", "برنامج جديد", "تطبيق جديد", "نظام جديد", "مستودع جديد",
        "new website", "create new website", "build new website", "new program",
        "new application", "create new app", "new system", "create new system",
        "new repository", "create repository", "create new repository",
    )
    return any(marker in normalized for marker in markers)


# ─── DIAGNOSTIC-ONLY logger ────────────────────────────────────────────────
# Instrumentation added to trace the has_executive_signals decision point in
# ExecutiveConversationEngine.execute(). This does NOT affect behavior — it
# only emits structured JSON log lines to stdout for runtime diagnosis.
_diag_handler = logging.StreamHandler(sys.stdout)
_diag_handler.setFormatter(logging.Formatter("%(message)s"))
_diag_logger = logging.getLogger("ameer.executive_conversation.diagnostic")
_diag_logger.setLevel(logging.INFO)
_diag_logger.propagate = False
if not _diag_logger.handlers:
    _diag_logger.addHandler(_diag_handler)


def _diag_log(event: str, **kwargs) -> None:
    """DIAGNOSTIC-ONLY: emit a structured JSON log line. Never raises."""
    try:
        record = {
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "event": event,
        }
        record.update(kwargs)
        _diag_logger.info(json.dumps(record, ensure_ascii=False))
    except Exception as exc:
        # Diagnostic logging must never break execution.
        import sys
        print(f"[_diag_log EXCEPTION] {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)


@dataclass
class ConversationPlannerState:
    # P0.7 Planner fields — Planner outputs only these four
    objectives: List[str] | None = None
    priorities: List[str] | None = None
    risks: List[str] | None = None
    recommendations: List[str] | None = None

    # Legacy fields kept for backward compatibility with existing code
    executive_objective: str = ""
    founder_objective: str = ""
    current_project_objective: str = ""
    detected_risks: List[str] | None = None
    missing_information: List[str] | None = None
    next_executive_action: str = ""

    def to_dict(self) -> dict:
        data = asdict(self)
        data["objectives"] = list(self.objectives or [])
        data["priorities"] = list(self.priorities or [])
        data["risks"] = list(self.risks or [])
        data["recommendations"] = list(self.recommendations or [])
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
        # SECURITY: Strip execution-state keys before writing to permanent
        # conversational memory.  Execution traces belong to ephemeral runtime
        # state and must not be promoted to permanent memory automatically.
        _EXECUTION_STATE_KEYS = {
            "execution_trace",
            "kernel_execution_trace",
            "execution_result",
            "pipeline_trace",
            "kernel_reply",
        }
        safe_state = {k: v for k, v in self._state.items() if k not in _EXECUTION_STATE_KEYS}
        # Apply credential sanitization before writing to disk.
        try:
            from kernel.credential_sanitizer import sanitize as _cs
            safe_state = _cs(safe_state)
        except Exception:
            pass
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(safe_state, ensure_ascii=False, indent=2), encoding="utf-8")

    def snapshot(self) -> dict:
        return dict(self._state)

    def build_context_block(self) -> str:
        parts: List[str] = []
        if self._state.get("unfinished_discussions"):
            items = " | ".join(self._state["unfinished_discussions"][:3])
            parts.append(f"نقاط لم تُغلق بعد: {items}")
        if self._state.get("pending_questions"):
            items = " | ".join(self._state["pending_questions"][:3])
            parts.append(f"أسئلة لا تزال مفتوحة: {items}")
        if self._state.get("executive_commitments"):
            items = " | ".join(self._state["executive_commitments"][:3])
            parts.append(f"التزامات جارية: {items}")
        if self._state.get("recurring_topics"):
            items = " | ".join(self._state["recurring_topics"][:3])
            parts.append(f"مواضيع متكررة: {items}")
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
        """
        P0.7 — Planner outputs only: objectives, priorities, risks, recommendations.
        All text is natural executive Arabic — no chatbot or template labels.
        """
        q = (query or "").strip()
        risks: List[str] = []
        missing: List[str] = []
        current_project = active_projects[0] if active_projects else ""

        # لا تعطل السجلات القديمة مرحلة تنفيذ مستمرة. تفويض أمير الافتراضي
        # يقتضي أن يعالجها أو يكمل العمل بدل طلب قرار جديد في كل مرة.
        normalized_q = q.lower().replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").replace("ى", "ي")
        continuation_terms = (
            "نفذ", "ابدأ", "اكمل", "كمل", "تابع", "استمر", "عدل", "اصلح", "اختبر",
            "جرب", "راجع", "انجز", "continue", "proceed", "execute", "implement", "test", "fix", "update",
        )
        is_continuation = any(term in normalized_q for term in continuation_terms)
        effective_running_tasks = [] if is_continuation else (running_tasks or [])
        effective_pending_approvals = [] if is_continuation else (pending_approvals or [])

        _stalled_statuses = {"pending", "blocked"}
        stalled_tasks = [t for t in effective_running_tasks if str(t.get("status", "")).lower() in _stalled_statuses]

        if effective_pending_approvals:
            risks.append("هناك موافقات معلقة قد تعطل المسار إذا لم تُحسم أولًا")
        if stalled_tasks:
            risks.append("مهام مفتوحة تشغل موارد وتحتاج إغلاقًا قبل فتح مسار جديد")
        if "fail" in workspace_summary.lower() or "error" in workspace_summary.lower():
            risks.append("بيئة العمل تحمل مؤشرات فشل تستحق مراجعة سريعة")
        if len(q) < 4:
            missing.append("الطلب مختصر — وضّح ما تريدي تحقيقه بالضبط")

        founder_objective = q or "متابعة العمل الجاري"
        executive_objective = executive_assessment or founder_objective

        # Core recommendation — natural, direct, no mechanical prefix.
        # Only stalled/blocked tasks warrant interrupting the flow.
        if effective_pending_approvals:
            next_action = "الأجدى أن نحسم طلب الموافقة أولًا حتى لا يتوقف كل شيء خلفه."
        elif stalled_tasks:
            next_action = "نغلق المهمة المفتوحة الأعلى أثرًا أولًا، ثم نفتح المسار الجديد."
        else:
            next_action = "أكمل على هذا."

        # P0.7 Planner fields
        objectives = [founder_objective]
        if current_project and current_project != founder_objective:
            objectives.append(f"المشروع الحالي: {current_project}")

        priorities: List[str] = []
        if effective_pending_approvals:
            priorities.append("حسم الموافقات المعلقة أولًا")
        if stalled_tasks:
            priorities.append("إغلاق المهام المفتوحة ذات الأثر الأعلى")
        if not priorities:
            priorities.append("التقدم في الطلب الحالي")

        recommendations = [next_action]
        if missing:
            recommendations.append(missing[0])

        return ConversationPlannerState(
            # P0.7 fields
            objectives=objectives,
            priorities=priorities,
            risks=risks,
            recommendations=recommendations,
            # Legacy fields kept for backward compatibility
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
                self._upsert_list("pending_questions", q, remove_if_answered=self._reply_resolves_question(r))
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

    def _reply_resolves_question(self, reply: str) -> bool:
        text = (reply or "").strip()
        if not text:
            return False
        resolution_markers = [
            "القرار",
            "الخطوة التالية",
            "تم الحسم",
            "أقترح",
            "ابدئي",
            "ابدأ",
        ]
        return any(marker in text for marker in resolution_markers)

    def _upsert_list(self, key: str, value: str, remove_if_answered: bool = False) -> None:
        items = [str(v) for v in self._state.get(key, []) if str(v).strip()]
        if remove_if_answered and value in items:
            items = [item for item in items if item != value]
        elif value not in items:
            items.insert(0, value)
        self._state[key] = items[:10]


class ExecutiveConversationEngine:
    """
    P0.7 — Executive Conversation Engine is the sole owner of the final reply.

    Builds the response from an empty buffer.
    Does NOT modify, append, prepend, or post-process any draft.
    """

    def __init__(self, workspace_root: str | Path) -> None:
        self.memory = PersistentConversationMemory(workspace_root)

    def execute(
        self,
        *,
        query: str,
        draft_reply: str = "",
        planner_state: ConversationPlannerState,
        conversation_context: str = "",
        persistent_memory_block: str = "",
        pending_approvals: Optional[List[dict]] = None,
        running_tasks: Optional[List[dict]] = None,
        active_projects: Optional[List[str]] = None,
        is_first_turn: bool = False,
        dry_run: bool = False,
        reasoning_output: Optional[dict] = None,
    ) -> dict:
        """
        P0.7 — Builds the final reply from an empty buffer.
        The draft_reply is used as the primary reply when the ECE has no meaningful
        executive context to add (no risks, no pending approvals, no initiative signals).
        When the ECE has real context to surface, it builds from scratch.
        """
        # DIAGNOSTIC-ONLY: unique trace id used to correlate the diagnostic
        # log lines emitted below. Does not affect behavior in any way.
        trace_id = f"{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{hash(query) % 10000:04d}"


        # Identity questions must always receive the constitutional identity reply
        # and must not be overridden by project-continuity or initiative text.
        _identity_tokens = {"من أنت", "من انت", "عرف بنفسك", "who are you", "what are you"}
        _q_lower = (query or "").strip().lower()
        _is_identity_query = any(tok in _q_lower for tok in _identity_tokens)
        if _is_identity_query:
            clean_draft = (draft_reply or "").strip()
            reply = clean_draft if clean_draft else "أنا أمير، شريكك التنفيذي."
            if not dry_run:
                self.memory.update_after_reply(query, reply, planner_state)
            return {
                "reply": reply,
                "planner_state": planner_state.to_dict(),
                "engine": "executive_conversation_engine",
                "response_owner": "ExecutiveConversationEngine",
                "memory_context_used": bool(conversation_context or persistent_memory_block),
            }

        # Only stalled/blocked tasks count as executive signals that justify
        # overriding the AI-generated reply.  Normal in-progress tasks do not
        # require proactive interruption.
        _stalled = [
            t for t in (running_tasks or [])
            if str(t.get("status", "")).lower() in {"pending", "blocked"}
        ]

        # Conversational requests must not be interrupted by stale persistent
        # state (pending tasks, active projects, planner risks).  Executive
        # signals are only relevant when the request itself is actionable
        # (execution, planning, decision).  Informational types (question,
        # analysis, memory, creative) and greetings are always conversational.
        _conversational_types = {
            "question",
            "greeting",
            "analysis",   # explain/why → informational, not executive
            "memory",     # "remember this" → bookkeeping, not executive override
            "creative",   # brainstorm/suggest → generative, not executive override
        }
        _request_type = (
            (reasoning_output or {}).get("reasoning", {}).get("request_type", "")
            if reasoning_output
            else ""
        )
        _is_conversational = _request_type in _conversational_types or not _request_type

        # DIAGNOSTIC-ONLY: snapshot of decision inputs right before the
        # has_executive_signals boolean is computed. No behavior is affected.
        _diag_log(
            "ece_pre_decision",
            trace_id=trace_id,
            query_preview=(query or "")[:80],
            request_type=_request_type,
            is_first_turn=is_first_turn,
            is_conversational=_is_conversational,
            active_projects_count=len(active_projects or []),
            pending_approvals_count=len(pending_approvals or []),
            stalled_count=len(_stalled),
            planner_risks_count=len((planner_state.risks or [])),
        )

        # Stale tasks and old approvals are context for reporting, never a gate
        # for a fresh internal execution.  The request guardian and the kernel
        # final gate remain the only authorities that can block the current turn.
        # This prevents a historical `pending`/`blocked` task from replacing a
        # site-build response with an instruction to close unrelated work first.
        _cond_pending_approvals = False
        _cond_stalled = False
        _cond_planner_risks = False
        _cond_first_turn_active_projects = False
        _guardian_status = (
            (reasoning_output or {}).get("reasoning", {}).get("guardian_status", "pass")
            if reasoning_output else "pass"
        )
        _root_asset_gate = _root_asset_creation_requested(query)
        # الحاجة إلى موافقة قديمة لا توقف أمير. فقط إنشاء أصل جذري جديد يبقي
        # هذه الحالة كطلب قرار للمالك؛ أما blocked فيبقى عائقًا تقنيًا صريحًا.
        _cond_guardian_not_pass = bool(
            _guardian_status == "blocked" or (_guardian_status == "needs_approval" and _root_asset_gate)
        )
        _diag_log(
            "ece_sub_conditions",
            trace_id=trace_id,
            cond_pending_approvals=_cond_pending_approvals,
            cond_stalled=_cond_stalled,
            cond_planner_risks=_cond_planner_risks,
            cond_first_turn_active_projects=_cond_first_turn_active_projects,
            cond_guardian_not_pass=_cond_guardian_not_pass,
        )

        has_executive_signals = _cond_guardian_not_pass

        # DIAGNOSTIC-ONLY: log the computed decision and which path will be
        # taken, before the branch is executed. No behavior is affected.
        _diag_log(
            "ece_decision",
            trace_id=trace_id,
            has_executive_signals=has_executive_signals,
            path=("_build_from_buffer" if has_executive_signals else "draft_reply"),
            draft_reply_preview=(draft_reply or "")[:120],
        )

        if has_executive_signals:
            reply = self._build_from_buffer(
                query=query,
                planner_state=planner_state,
                pending_approvals=pending_approvals,
                running_tasks=running_tasks,
                active_projects=active_projects,
                is_first_turn=is_first_turn,
                reasoning_output=reasoning_output,
                dry_run=dry_run,
            )
        else:
            # No meaningful executive state to add — use the provider/brain reply directly
            clean_draft = (draft_reply or "").strip()
            if clean_draft:
                reply = clean_draft
            else:
                # Last resort: build from planner (will be a short natural fallback)
                reply = self._build_from_buffer(
                    query=query,
                    planner_state=planner_state,
                    pending_approvals=pending_approvals,
                    running_tasks=running_tasks,
                    active_projects=active_projects,
                    is_first_turn=is_first_turn,
                    reasoning_output=reasoning_output,
                    dry_run=dry_run,
                )

        # DIAGNOSTIC-ONLY: log the finalized reply and the path actually taken,
        # right before returning. No behavior is affected.
        _diag_log(
            "ece_final_reply",
            trace_id=trace_id,
            path_taken=("_build_from_buffer" if has_executive_signals else "draft_reply"),
            final_reply_preview=(reply or "")[:120],
        )

        if not dry_run:
            self.memory.update_after_reply(query, reply, planner_state)
        return {
            "reply": reply,
            "planner_state": planner_state.to_dict(),
            "engine": "executive_conversation_engine",
            "response_owner": "ExecutiveConversationEngine",
            "memory_context_used": bool(conversation_context or persistent_memory_block),
        }

    def _build_from_buffer(
        self,
        *,
        query: str,
        planner_state: ConversationPlannerState,
        pending_approvals: Optional[List[dict]],
        running_tasks: Optional[List[dict]],
        active_projects: Optional[List[str]],
        is_first_turn: bool,
        reasoning_output: Optional[dict],
        dry_run: bool,
    ) -> str:
        """
        Builds the reply from scratch using planner state and reasoning output.
        No draft is used; no append/prepend/post-processing occurs.
        Tone: natural executive Arabic — no template labels, no chatbot phrases.
        """
        parts: List[str] = []

        # Proactive initiative — only when there is a real traceable reason
        if pending_approvals:
            detail = str(pending_approvals[0].get("description") or pending_approvals[0].get("summary") or "قرار معلق")
            if not dry_run:
                self.memory.record_initiative("pending_approval", detail)
            parts.append(f"عندي نقطة تحتاج منك قرارًا قبل أي تقدم: {detail}.")
        elif is_first_turn and running_tasks:
            if not dry_run:
                self.memory.record_initiative("unfinished_conversation", "running_tasks")
            parts.append("من آخر جلسة بقي مسار مفتوح لم يُغلق بعد — هذا سيؤثر على ما نبدأه الآن.")
        elif is_first_turn and active_projects:
            if not dry_run:
                self.memory.record_initiative("project_continuity", active_projects[0])
            parts.append(f"نكمل من حيث توقفنا في {active_projects[0]}.")

        # Guardian gate
        if reasoning_output:
            reasoning = reasoning_output.get("reasoning", {})
            guardian_status = reasoning.get("guardian_status", "pass")
            if guardian_status == "needs_approval" and _root_asset_creation_requested(query):
                guardian_reason = reasoning.get("guardian_reason", "")
                reason_text = f" ({guardian_reason})" if guardian_reason else ""
                parts.append(f"إنشاء أصل رقمي مستقل جديد يحتاج موافقتك مرة واحدة{reason_text}. هل أبدأ؟")
                return " ".join(parts).strip()
            if guardian_status == "blocked":
                parts.append(
                    "هذا الطلب خارج ما أستطيع تنفيذه بشكل مباشر. "
                    "أستطيع أن أقترح مسارًا بديلًا يحقق نفس النتيجة."
                )
                return " ".join(parts).strip()

        # Risks — woven into the response naturally, not as a labelled list
        risks = planner_state.risks or planner_state.detected_risks or []
        if risks:
            risk_text = risks[0]
            parts.append(f"لفت انتباهي أن {risk_text}.")

        # Core action — the recommendation, stated directly
        recommendations = planner_state.recommendations or []
        if recommendations:
            parts.append(recommendations[0])
        elif planner_state.next_executive_action:
            parts.append(planner_state.next_executive_action)
        else:
            # Natural fallback when nothing concrete is available
            q_short = (query or "").strip()[:80]
            if q_short:
                parts.append(f"دعيني أتابع معك على هذا.")
            else:
                parts.append("أنا معك، حددي الخطوة التالية.")

        # Missing information — ask one direct question
        missing = planner_state.missing_information or []
        if missing and "؟" not in " ".join(parts):
            parts.append(f"{missing[0]}؟")

        reply = re.sub(r"\s{2,}", " ", " ".join(parts)).strip()
        return reply or "أنا معك."

    def _build_initiative(
        self,
        *,
        pending_approvals: Optional[List[dict]],
        running_tasks: Optional[List[dict]],
        active_projects: Optional[List[str]],
        is_first_turn: bool,
        dry_run: bool = False,
    ) -> str:
        """Kept for backward compatibility."""
        if pending_approvals:
            detail = str(pending_approvals[0].get("description") or pending_approvals[0].get("summary") or "قرار معلق")
            if not dry_run:
                self.memory.record_initiative("pending_approval", detail)
            return f"عندي نقطة تحتاج منك قرارًا قبل أي تقدم: {detail}."
        if is_first_turn and running_tasks:
            if not dry_run:
                self.memory.record_initiative("unfinished_conversation", "running_tasks")
            return "من آخر جلسة بقي مسار مفتوح لم يُغلق بعد — هذا سيؤثر على ما نبدأه الآن."
        if is_first_turn and active_projects:
            if not dry_run:
                self.memory.record_initiative("project_continuity", active_projects[0])
            return f"نكمل من حيث توقفنا في {active_projects[0]}."
        return ""

    def _enforce_style(self, reply: str, planner_state: ConversationPlannerState) -> str:
        """Kept for backward compatibility — not used in P0.7 execute()."""
        text = (reply or "").strip()
        # Remove chatbot and assistant phrases
        chatbot_phrases = {
            "كيف أستطيع مساعدتك؟": "",
            "كيف أساعدك؟": "",
            "هل تحتاج شيئًا آخر؟": "",
            "يسعدني مساعدتك": "",
            "يسعدني أن أساعدك": "",
            "مرحبا،": "",
            "مرحبًا،": "",
            "مرحبا": "",
            "مرحبًا": "",
            "بكل سرور": "",
            "بالتأكيد": "",
            "حاضر، تمت معالجة طلبك. إذا أردت تفاصيل إضافية أخبرني.": "أنا معك.",
            "حاضر، أتابع معك على هذا الطلب.": "أنا معك.",
        }
        for old, new in chatbot_phrases.items():
            text = text.replace(old, new)
        text = re.sub(r"\bforward\b", "للأمام", text, flags=re.IGNORECASE)
        text = re.sub(r"\s{2,}", " ", text).strip()
        return text or "أنا معك."

