"""
executive_kernel.py
===================
Executive Operating Kernel — قلب نظام أمير التشغيلي.

ينسّق جميع المكونات ويُهيّئها بالترتيب الصحيح.
يمتلك الـ lifecycle الكامل لكل جلسة وكل طلب.
لا شيء يُنفَّذ خارج الـ Kernel.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Optional

# Add code root to path for sibling imports
_CODE_ROOT = str(Path(__file__).resolve().parent.parent)
if _CODE_ROOT not in sys.path:
    sys.path.insert(0, _CODE_ROOT)

from kernel.state_manager import ExecutiveStateManager
from kernel.decision_engine import DecisionEngine
from kernel.approval_gate import ApprovalGate
from kernel.feedback_engine import FeedbackEngine
from kernel.learning_engine import LearningEngine
from kernel.memory_governance import MemoryGovernanceEngine
from kernel.capability_registry import CapabilityRegistry
from kernel.permission_registry import PermissionRegistry
from kernel.execution_authorization import ExecutionAuthorization
from kernel.plan_validator import PlanValidator
from kernel.scheduler import Scheduler
from kernel.executor_file import FileExecutor
from context.workspace_awareness import WorkspaceAwareness
from context.session_context import SessionContext
from context.founder_profile import FounderProfile
from executive_conversation import PersistentConversationMemory


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class ExecutiveKernel:
    """
    السلطة التنفيذية المركزية لنظام أمير.

    المسؤوليات:
    1. تهيئة كل المكونات عند الـ startup
    2. إدارة lifecycle الجلسة
    3. توفير سياق متكامل لكل طلب
    4. تتبع الحالة التنفيذية الدائمة
    """

    def __init__(self, workspace_root: str | Path) -> None:
        self._root = Path(workspace_root).resolve()
        self._initialized = False
        self._health: dict = {}
        self._first_turn: bool = False

        # Component registry
        self.state: ExecutiveStateManager = ExecutiveStateManager(self._root)
        self.decisions: DecisionEngine = DecisionEngine(self._root)
        self.approvals: ApprovalGate = ApprovalGate(self._root)
        self.feedback: FeedbackEngine = FeedbackEngine(self._root)
        self.learning: LearningEngine = LearningEngine(self._root, self.feedback)
        self.memory_governance: MemoryGovernanceEngine = MemoryGovernanceEngine(self._root, self.approvals)
        self.workspace: WorkspaceAwareness = WorkspaceAwareness(self._root)
        self.session: SessionContext = SessionContext()
        self.founder: FounderProfile = FounderProfile(self._root)
        self.conversation_memory: PersistentConversationMemory = PersistentConversationMemory(self._root)
        # P0.6 — Executive Capability Governance
        self.capabilities: CapabilityRegistry = CapabilityRegistry(self._root)
        self.permissions: PermissionRegistry = PermissionRegistry(self._root)
        self.execution_auth: ExecutionAuthorization = ExecutionAuthorization(
            self._root, self.capabilities, self.permissions
        )
        # P1.3 — Plan Validator (the single gate before the Scheduler)
        self.plan_validator: PlanValidator = PlanValidator(
            self._root,
            capability_registry=self.capabilities,
            permission_registry=self.permissions,
        )
        self.scheduler: Scheduler = Scheduler(self._root, self.state)
        self.file_executor: FileExecutor = FileExecutor(self._root)

    # ── Startup helpers ───────────────────────────────────────────────────────

    def _extract_active_projects(self) -> list:
        """Extract active project names from the founder's Projects.md memory file."""
        import re
        projects_text = self.founder.get_section("Projects.md") or ""
        if not projects_text:
            return self.state.active_projects  # keep existing

        found: list = []
        for line in projects_text.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("---"):
                continue
            # Pick heading lines or bullet items that look like project names
            name_match = re.match(r"^(?:##?\s+|[-*]\s+)(.+)$", line)
            if name_match:
                name = name_match.group(1).strip(" :|")
                if name and len(name) < 80:
                    found.append(name)
        return found[:10] if found else self.state.active_projects

    # ── Startup ───────────────────────────────────────────────────────────────

    def boot(self) -> dict:
        """
        تهيئة كاملة عند الـ startup.
        يُعيد تقرير صحة النظام.
        """
        self._health = {}
        errors = []
        scan: dict = {}
        summary = ""

        # 1. State Manager
        try:
            self.state.mark_session_start()
            self._health["state_manager"] = "ok"
        except Exception as exc:
            self._health["state_manager"] = f"error: {exc}"
            errors.append("state_manager")

        # 2. Founder Memory (Founder Profile + Goals + Projects + Preferences)
        try:
            self.founder.load()
            founder_ctx = {"loaded": True, "sections": list(self.founder.sections.keys())}
            self.state.set_founder_context(founder_ctx)
            self._health["founder_profile"] = "ok"
        except Exception as exc:
            self._health["founder_profile"] = f"error: {exc}"
            errors.append("founder_profile")

        # 3. Workspace Status + Active Projects + Pending Tasks + Pending Approvals
        try:
            scan = self.workspace.scan()
            summary = self.workspace.build_executive_summary(scan)
            self.state.set_workspace_summary(summary)

            # Persist structured startup data into state so every request can read it
            active_projects = self._extract_active_projects()
            if active_projects:
                self.state.set_active_projects(active_projects)

            pending_tasks = scan.get("tasks", {}).get("pending", [])
            if pending_tasks:
                # Merge new tasks without duplicating existing ones
                existing_ids = {t.get("id") for t in self.state.running_tasks}
                for task in pending_tasks:
                    if task.get("id") not in existing_ids:
                        self.state.add_task(task)

            # Pending approvals from workspace scan are already in state (persisted); no re-add needed.

            self._health["workspace_awareness"] = "ok"
        except Exception as exc:
            self._health["workspace_awareness"] = f"error: {exc}"
            errors.append("workspace_awareness")

        # 4. Session Context
        try:
            self.session.clear()
            self._health["session_context"] = "ok"
        except Exception as exc:
            self._health["session_context"] = f"error: {exc}"
            errors.append("session_context")

        try:
            _ = self.conversation_memory.snapshot()
            self._health["persistent_conversation_memory"] = "ok"
        except Exception as exc:
            self._health["persistent_conversation_memory"] = f"error: {exc}"
            errors.append("persistent_conversation_memory")

        # 5. Decision Engine
        try:
            _ = self.decisions.snapshot()
            self._health["decision_engine"] = "ok"
        except Exception as exc:
            self._health["decision_engine"] = f"error: {exc}"
            errors.append("decision_engine")

        # 6. Approval Gate
        try:
            _ = self.approvals.snapshot()
            self._health["approval_gate"] = "ok"
        except Exception as exc:
            self._health["approval_gate"] = f"error: {exc}"
            errors.append("approval_gate")

        # 7. Feedback Engine
        try:
            _ = self.feedback.snapshot()
            self._health["feedback_engine"] = "ok"
        except Exception as exc:
            self._health["feedback_engine"] = f"error: {exc}"
            errors.append("feedback_engine")

        # 8. Learning Engine
        try:
            _ = self.learning.snapshot()
            self._health["learning_engine"] = "ok"
        except Exception as exc:
            self._health["learning_engine"] = f"error: {exc}"
            errors.append("learning_engine")

        # 9. Memory Governance
        try:
            _ = self.memory_governance.snapshot()
            self._health["memory_governance"] = "ok"
        except Exception as exc:
            self._health["memory_governance"] = f"error: {exc}"
            errors.append("memory_governance")

        # 10. Capability Registry (P0.6)
        try:
            _ = self.capabilities.snapshot()
            self._health["capability_registry"] = "ok"
        except Exception as exc:
            self._health["capability_registry"] = f"error: {exc}"
            errors.append("capability_registry")

        # 11. Permission Registry (P0.6)
        try:
            _ = self.permissions.snapshot()
            self._health["permission_registry"] = "ok"
        except Exception as exc:
            self._health["permission_registry"] = f"error: {exc}"
            errors.append("permission_registry")

        # 12. Execution Authorization (P0.6)
        try:
            _ = self.execution_auth.snapshot()
            self._health["execution_authorization"] = "ok"
        except Exception as exc:
            self._health["execution_authorization"] = f"error: {exc}"
            errors.append("execution_authorization")

        overall = "degraded" if errors else "running"
        self.state.set_runtime_status(overall)
        self._initialized = True
        # Track whether this is the very first conversation after startup
        self._first_turn = True

        return {
            "status": overall,
            "booted_at": _now_iso(),
            "components": self._health,
            "errors": errors,
            "workspace_summary": summary,
            "active_projects": self.state.active_projects,
            "pending_tasks": [t for t in self.state.running_tasks],
            "pending_approvals": self.state.pending_approvals,
        }

    # ── Per-Request Lifecycle ─────────────────────────────────────────────────

    def before_request(self, query: str) -> dict:
        """
        يُعيد السياق الكامل المطلوب قبل معالجة كل طلب.
        يُدار داخل ameer_server.py قبل استدعاء Executive Brain.

        Pipeline order:
          Executive State → Workspace Awareness → Founder Profile
          → Session Context → (returned to Brain)
        """
        if not self._initialized:
            self.boot()

        # Consume the first-turn flag so briefing fires only once per startup
        is_first_turn = getattr(self, "_first_turn", False)
        if is_first_turn:
            self._first_turn = False

        # Record user turn in session context
        self.session.add_user_message(query)

        return {
            "conversation_context": self.session.build_context_block(),
            "founder_context": self.founder.build_context_block(),
            "workspace_summary": self.state.workspace_summary,
            "pending_approvals": self.state.pending_approvals,
            "pending_approval_requests": self.approvals.pending(),
            "active_projects": self.state.active_projects,
            "running_tasks": self.state.running_tasks,
            "executive_assessment": self.state.executive_assessment,
            "persistent_conversation_memory": self.conversation_memory.snapshot(),
            "persistent_memory_context": self.conversation_memory.build_context_block(),
            "learned_preferences": self.learning.get_preferences(),
            "learned_preferences_context": self.learning.build_context_block(),
            "memory_governance": self.memory_governance.snapshot(),
            "session_count": self.state.session_count,
            "is_follow_up": self.session.is_follow_up(),
            "is_first_turn": is_first_turn,
            "proactive_briefing": self._build_proactive_briefing() if is_first_turn else "",
            "capability_governance": self.capabilities.snapshot(),
            "pending_execution_requests": len(self.execution_auth.pending_requests()),
        }

    def after_request(self, reply: str) -> None:
        """يُسجّل رد أمير في تاريخ المحادثة."""
        if reply:
            self.session.add_assistant_message(reply)

    # ── Proactive Briefing ────────────────────────────────────────────────────

    def _build_proactive_briefing(self) -> str:
        """
        يُنتج إحاطة استباقية عند أول رسالة في الجلسة.
        تشمل: المشاريع النشطة، الموافقات المعلّقة، القرارات الأخيرة.
        """
        parts: list = []

        active = self.state.active_projects
        if active:
            names = "، ".join(active[:5])
            parts.append(f"المشاريع النشطة: {names}.")

        pending_approvals = self.approvals.pending()
        if pending_approvals:
            count = len(pending_approvals)
            desc = pending_approvals[0].get("description", "")
            parts.append(f"لديك {count} طلب موافقة معلّق" + (f': "{desc}"' if desc else "") + ".")

        pending_decisions = self.decisions.pending()
        if pending_decisions:
            count = len(pending_decisions)
            title = pending_decisions[0].get("title", "")
            parts.append(f"لديك {count} قرار قيد الانتظار" + (f': "{title}"' if title else "") + ".")

        running_tasks = self.state.running_tasks
        if running_tasks:
            count = len(running_tasks)
            parts.append(f"المهام الجارية: {count}.")

        return " ".join(parts) if parts else ""

    # ── Task Execution (P1.3 gated pipeline) ──────────────────────────────────

    def execute_task(self, tasks: list) -> dict:
        """
        نقطة الدخول الوحيدة لتنفيذ مهام.

        المسار الإلزامي:
            ExecutiveKernel.execute_task()
                ↓
            PlanValidator   ← البوابة الوحيدة
                ↓
            Scheduler (P1.4)
                ↓
            ExecutionEngine (P1.5+)

        لا يُسمح لأي مكون بتجاوز PlanValidator.

        يُعيد:
        {
            "accepted": bool,
            "validation": { ... },   # مخرج PlanValidator
            "tasks_queued": int,     # عدد المهام المقبولة للجدولة
        }
        """
        validation = self.plan_validator.validate(tasks)

        if not validation["valid"]:
            return {
                "accepted": False,
                "validation": validation,
                "schedule": {
                    "accepted": False,
                    "blocked": [],
                    "batches": [],
                    "execution_order": [],
                    "summary": {"total": len(tasks), "scheduled": 0, "blocked": 0, "parallel_batches": 0},
                },
                "execution": {
                    "completed": 0,
                    "failed": 0,
                    "blocked": 0,
                    "results": [],
                },
                "tasks_queued": 0,
            }

        schedule = self.scheduler.schedule(tasks)

        for task in tasks:
            stored_task = dict(task)
            if any(item.get("id") == task.get("id") for item in schedule.get("blocked", [])):
                stored_task["status"] = "blocked"
            else:
                stored_task["status"] = "pending"
            self.state.add_task(stored_task)

        execution_results = []
        completed = 0
        failed = 0
        blocked = len(schedule.get("blocked", []))

        if schedule.get("accepted"):
            for batch in schedule.get("batches", []):
                for task in batch.get("tasks", []):
                    task_id = task.get("id")
                    executor = str(task.get("executor", "")).lower()
                    self.state.update_task(task_id, "in_progress")
                    if executor == "file":
                        outcome = self.file_executor.execute(task)
                    else:
                        outcome = {
                            "task_id": task_id,
                            "status": "failed",
                            "reason": "executor_not_implemented",
                            "executor": executor,
                        }
                    execution_results.append(outcome)
                    if outcome.get("status") == "completed":
                        completed += 1
                        self.state.update_task(task_id, "done", result=str(outcome))
                    elif outcome.get("status") == "blocked":
                        blocked += 1
                        self.state.update_task(task_id, "blocked", result=str(outcome))
                    else:
                        failed += 1
                        self.state.update_task(task_id, "failed", result=str(outcome))

        return {
            "accepted": schedule.get("accepted", False),
            "validation": validation,
            "schedule": schedule,
            "execution": {
                "completed": completed,
                "failed": failed,
                "blocked": blocked,
                "results": execution_results,
            },
            "tasks_queued": schedule.get("summary", {}).get("scheduled", 0),
        }

    # ── Decision & Approval helpers ───────────────────────────────────────────

    def record_decision(
        self,
        title: str,
        reason: str,
        category: str = "other",
        expected_outcome: str = "",
    ) -> str:
        """تسجيل قرار تنفيذي. يُعيد decision_id."""
        return self.decisions.record(
            title=title,
            reason=reason,
            category=category,
            expected_outcome=expected_outcome,
        )

    def request_approval(
        self,
        action: str,
        description: str,
        requested_by: str = "executive_brain",
    ) -> str:
        """طلب موافقة المؤسسة على إجراء حساس. يُعيد approval_id."""
        return self.approvals.request(
            action=action,
            description=description,
            requested_by=requested_by,
        )

    # ── Health ────────────────────────────────────────────────────────────────

    def health(self) -> dict:
        mem_snap = self.memory_governance.snapshot()
        return {
            "initialized": self._initialized,
            "status": self.state.snapshot().get("runtime_status", "unknown"),
            "session_turns": len(self.session),
            "founder_loaded": self.founder.is_loaded,
            "pending_approvals": len(self.state.pending_approvals),
            "pending_approval_requests": len(self.approvals.pending()),
            "pending_decisions": len(self.decisions.pending()),
            "feedback_total": self.feedback.snapshot().get("total", 0),
            "learning_log_entries": self.learning.snapshot().get("log_entries", 0),
            "founder_memory_items": mem_snap["layers"]["founder_memory"]["count"],
            "learned_knowledge_items": mem_snap["layers"]["learned_knowledge"]["count"],
            "memory_pending_approvals": mem_snap.get("pending_candidates", 0),
            "components": self._health,
            "active_capabilities": self.capabilities.snapshot()["by_status"],
            "pending_execution_requests": self.execution_auth.snapshot()["pending_count"],
        }

    # ── Workspace refresh ─────────────────────────────────────────────────────

    def refresh_workspace(self) -> str:
        """إعادة فحص بيئة العمل وتحديث الملخص."""
        try:
            scan = self.workspace.scan()
            summary = self.workspace.build_executive_summary(scan)
            self.state.set_workspace_summary(summary)
            return summary
        except Exception:
            return ""
