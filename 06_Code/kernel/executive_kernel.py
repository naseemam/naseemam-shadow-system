"""
executive_kernel.py
===================
Executive Operating Kernel — قلب نظام أمير التشغيلي.

ينسّق جميع المكونات ويُهيّئها بالترتيب الصحيح.
يمتلك الـ lifecycle الكامل لكل جلسة وكل طلب.
لا شيء يُنفَّذ خارج الـ Kernel.
"""

from __future__ import annotations

import uuid

import json
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
from kernel.execution_authorization import (
    ExecutionAuthorization,
    file_create_permission_scope,
    file_read_permission_scope,
    shell_run_permission_scope,
)
from kernel.execution_boundary import ExecutionBoundary
from kernel.tool_registry import ToolRegistry
from kernel.tool_dispatcher import ToolDispatcher
from kernel.plan_validator import PlanValidator
from kernel.scheduler import Scheduler
from kernel.executor_file import FileExecutor
from kernel.executor_shell import ShellExecutor
from kernel.task_decomposer import TaskDecomposer
from context.workspace_awareness import WorkspaceAwareness
from context.session_context import SessionContext
from context.founder_profile import FounderProfile
from executive_conversation import PersistentConversationMemory
from kernel.worker_runtime import WorkerRuntimeRegistry
from kernel.worker_adapters import configure_workers_from_env
from kernel.central_audit import CentralExecutionAudit
from kernel.executive_orchestrator import ExecutiveOrchestrator
from kernel.shadow_foundation import ShadowFoundation


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
        # Worker runtime registry: registration alone is not readiness or execution.
        self.central_audit = CentralExecutionAudit(self._root)
        self.worker_runtime: WorkerRuntimeRegistry = WorkerRuntimeRegistry(self._root, audit=self.central_audit)
        self.worker_runtime_config = configure_workers_from_env(self.worker_runtime)
        # Shared Shadow System foundation: identity, projects, roles, and policy.
        # This is metadata/governance only; it does not execute external effects.
        self.shadow_foundation: ShadowFoundation = ShadowFoundation(self._root)
        self.orchestrator = ExecutiveOrchestrator(self._root, runtime=self.worker_runtime, audit=self.central_audit)
        # P0.6 — Executive Capability Governance
        self.capabilities: CapabilityRegistry = CapabilityRegistry(self._root)
        self.permissions: PermissionRegistry = PermissionRegistry(self._root)
        self._enable_file_read_permission()
        self._enable_shell_run_permission()
        self._enable_file_create_permission()
        self.execution_auth: ExecutionAuthorization = ExecutionAuthorization(
            self._root, self.capabilities, self.permissions
        )
        self.execution_boundary: ExecutionBoundary = ExecutionBoundary(
            approval_gate=self.approvals,
            execution_auth=self.execution_auth,
        )
        self.tool_registry: ToolRegistry = ToolRegistry()
        # P1.3 — Plan Validator (the single gate before the Scheduler)
        self.plan_validator: PlanValidator = PlanValidator(
            self._root,
            capability_registry=self.capabilities,
            permission_registry=self.permissions,
        )
        self.scheduler: Scheduler = Scheduler(self._root, self.state)
        self.file_executor: FileExecutor = FileExecutor(self._root)
        self.shell_executor: ShellExecutor = ShellExecutor(self._root)
        self.tool_dispatcher: ToolDispatcher = ToolDispatcher(
            tool_registry=self.tool_registry,
            execution_boundary=self.execution_boundary,
            execution_authorization=self.execution_auth,
            approval_gate=self.approvals,
            executor=self.file_executor.execute,
            shell_executor=self.shell_executor.execute,
            workspace_root=self._root,
        )
        self.task_decomposer: TaskDecomposer = TaskDecomposer(str(self._root))

    def _enable_file_read_permission(self) -> None:
        file_cap = self.capabilities.get_by_name("file_operations")
        if file_cap is None:
            return
        existing = self.permissions.get_for_capability(file_cap["capability_id"])
        expected_scope = file_read_permission_scope()
        if (
            existing
            and existing.get("permission_status") == "granted"
            and existing.get("enabled", False)
            and existing.get("scope") == expected_scope
        ):
            return
        self.permissions.grant(
            file_cap["capability_id"],
            scope=expected_scope,
            granted_by="system:file.read_activation",
        )

    def _enable_shell_run_permission(self) -> None:
        shell_cap = self.capabilities.get_by_name("shell_execution")
        if shell_cap is None:
            return
        existing = self.permissions.get_for_capability(shell_cap["capability_id"])
        expected_scope = shell_run_permission_scope()
        if (
            existing
            and existing.get("permission_status") == "granted"
            and existing.get("enabled", False)
        ):
            return
        self.permissions.grant(
            shell_cap["capability_id"],
            scope=expected_scope,
            granted_by="system:shell.run_activation",
        )

    def _enable_file_create_permission(self) -> None:
        """
        Bootstrap check: ensure the file.create permission card always exists
        in a granted state at startup, independent of preDeployCommand or any
        other external setup step.

        This card is keyed by the tool_name "file.create" (not the
        file_operations capability UUID) so it stays independent from the
        file_operations capability card used elsewhere.
        """
        expected_scope = file_create_permission_scope()
        existing = self.permissions.get_for_capability("file.create")
        if (
            existing
            and existing.get("permission_status") == "granted"
            and existing.get("enabled", False)
            and existing.get("scope") == expected_scope
        ):
            return
        self.permissions.grant(
            "file.create",
            scope=expected_scope,
            granted_by="system:file.create_activation",
        )

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

        # 13. Tool Registry
        try:
            _ = self.tool_registry.list_tools()
            self._health["tool_registry"] = "ok"
        except Exception as exc:
            self._health["tool_registry"] = f"error: {exc}"
            errors.append("tool_registry")

        # 14. Execution Boundary
        try:
            _ = self.execution_boundary.evaluate(
                guardian={"status": "pass"},
                request_type="question",
                intent="health_check",
                capability_name="file_operations",
                action="write",
                context={"source": "kernel_boot_health"},
                requested_by="executive_kernel",
            )
            self._health["execution_boundary"] = "ok"
        except Exception as exc:
            self._health["execution_boundary"] = f"error: {exc}"
            errors.append("execution_boundary")

        # 15. Tool Dispatcher
        try:
            _ = self.tool_dispatcher
            self._health["tool_dispatcher"] = "ok"
        except Exception as exc:
            self._health["tool_dispatcher"] = f"error: {exc}"
            errors.append("tool_dispatcher")

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
            "worker_runtime": self.worker_runtime.snapshot(),
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

    @staticmethod
    def _tool_name_for_action(action: str, executor_name: str = "file") -> Optional[str]:
        normalized = str(action or "").strip().lower()
        if executor_name == "shell":
            if normalized in {"run", "execute"}:
                return "shell.run"
            return None
        # file executor (default)
        if normalized == "read":
            return "file.read"
        if normalized in {"write", "create"}:
            return "file.create"
        return None

    def _dispatch_task_tool(
        self,
        task: dict,
        *,
        guardian: Optional[dict],
        request_type: str,
        intent: str,
        requested_by: str,
    ) -> dict:
        if self.tool_dispatcher is None:
            return {
                "decision": "DENY",
                "allowed": False,
                "reason": "tool_dispatcher_unavailable",
                "executed": False,
                "result": None,
            }

        executor_name = str(task.get("executor", "")).strip().lower()
        _SUPPORTED_EXECUTORS = {"file", "shell"}
        if executor_name not in _SUPPORTED_EXECUTORS:
            return {
                "decision": "DENY",
                "allowed": False,
                "reason": "executor_not_supported",
                "executed": False,
                "result": {
                    "task_id": task.get("id"),
                    "status": "failed",
                    "reason": "executor_not_implemented",
                    "executor": executor_name,
                },
            }

        tool_name = self._tool_name_for_action(task.get("action", ""), executor_name)
        if not tool_name:
            return {
                "decision": "DENY",
                "allowed": False,
                "reason": "tool_not_registered",
                "executed": False,
                "result": {
                    "task_id": task.get("id"),
                    "status": "failed",
                    "reason": "unsupported_action",
                    "action": task.get("action", ""),
                },
            }

        # Build context appropriate for the executor type.
        if executor_name == "shell":
            dispatch_context = {
                "task_id": task.get("id"),
                "command": task.get("command"),
                "cwd": task.get("cwd"),
                "env": task.get("env"),
                "timeout": task.get("timeout"),
                "executor": executor_name,
                "action": task.get("action"),
                "executor_payload": dict(task),
            }
        else:
            dispatch_context = {
                "task_id": task.get("id"),
                "target": task.get("target"),
                "content": task.get("content"),
                "executor": executor_name,
                "action": task.get("action"),
                "executor_payload": dict(task),
            }

        return self.tool_dispatcher.dispatch(
            tool_name=tool_name,
            context=dispatch_context,
            guardian=guardian,
            request_type=request_type,
            intent=intent,
            requested_by=requested_by,
        )

    @staticmethod
    def _serialize_boundary_result(boundary_result: object | None) -> dict:
        if boundary_result is None:
            return {}
        verdict = getattr(boundary_result, "verdict", None)
        if hasattr(verdict, "value"):
            verdict_value = str(verdict.value)
        else:
            verdict_value = str(verdict) if verdict is not None else ""
        return {
            "verdict": verdict_value,
            "reason": getattr(boundary_result, "reason", ""),
            "request_id": getattr(boundary_result, "request_id", None),
            "authorization_request_id": getattr(boundary_result, "authorization_request_id", None),
            "detail": getattr(boundary_result, "detail", {}) or {},
        }

    def _governance_step_from_dispatch(self, dispatch_result: dict) -> dict:
        boundary_payload = self._serialize_boundary_result(dispatch_result.get("boundary_result"))
        auth_detail = {}
        if isinstance(boundary_payload.get("detail"), dict):
            auth_detail = boundary_payload.get("detail") or {}
        return {
            "dispatcher": {
                "decision": dispatch_result.get("decision"),
                "reason": dispatch_result.get("reason"),
            },
            "execution_boundary": boundary_payload,
            "execution_authorization": {
                "request_id": auth_detail.get("request_id"),
                "status": auth_detail.get("status"),
                "reason": auth_detail.get("reason"),
                "capability_name": auth_detail.get("capability_name"),
                "action": auth_detail.get("action"),
            },
        }

    def execute_task(
        self,
        tasks: list,
        *,
        guardian: Optional[dict] = None,
        request_type: str = "execution",
        intent: str = "execute_tasks",
        requested_by: str = "executive_kernel",
        register_tasks: bool = True,
    ) -> dict:
        """
        نقطة الدخول الوحيدة لتنفيذ مهام.

        المسار الإلزامي:
            ExecutiveKernel.execute_task()
                ↓
            PlanValidator   ← البوابة الوحيدة
                ↓
            Scheduler (P1.4)
                ↓
            ToolDispatcher → ToolRegistry → ExecutionBoundary → ExecutionAuthorization → FileExecutor

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

        if register_tasks:
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
        blocked = 0

        if schedule.get("accepted"):
            for batch in schedule.get("batches", []):
                for task in batch.get("tasks", []):
                    task_id = task.get("id")
                    self.state.update_task(task_id, "in_progress")
                    dispatch_result = self._dispatch_task_tool(
                        task,
                        guardian=guardian,
                        request_type=request_type,
                        intent=intent,
                        requested_by=requested_by,
                    )
                    if dispatch_result.get("executed"):
                        outcome = dispatch_result.get("result") or {
                            "task_id": task_id,
                            "status": "failed",
                            "reason": "executor_result_missing",
                        }
                        if isinstance(outcome, dict):
                            outcome = {
                                **outcome,
                                "governance": self._governance_step_from_dispatch(dispatch_result),
                            }
                    else:
                        outcome = {
                            "task_id": task_id,
                            "status": "blocked",
                            "reason": dispatch_result.get("reason", "dispatcher_denied"),
                            "decision": dispatch_result.get("decision", "DENY"),
                            "tool": (dispatch_result.get("execution_request") or {}).get("tool_name"),
                            "governance": self._governance_step_from_dispatch(dispatch_result),
                        }
                    execution_results.append(outcome)
                    if outcome.get("status") == "completed":
                        completed += 1
                        self.state.update_task(task_id, "done", result=json.dumps(outcome, ensure_ascii=False))
                    elif outcome.get("status") == "blocked":
                        blocked += 1
                        self.state.update_task(task_id, "blocked", result=json.dumps(outcome, ensure_ascii=False))
                    else:
                        failed += 1
                        self.state.update_task(task_id, "failed", result=json.dumps(outcome, ensure_ascii=False))

        execution_accepted = (
            schedule.get("accepted", False)
            and failed == 0
            and blocked == 0
        )

        return {
            "accepted": execution_accepted,
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

    def execute_command(
        self,
        command: str,
        *,
        guardian: Optional[dict] = None,
        request_type: str = "execution",
        requested_by: str = "executive_kernel",
    ) -> dict:
        """
        المسار الكامل: أمر بشري → Task Batch → PlanValidator → Scheduler → ToolDispatcher → FileExecutor.

        يُعيد trace كامل لكل خطوة في الـ Pipeline.
        """
        # 1. Executive Brain — intent detection (via TaskDecomposer)
        decomposition = self.task_decomposer.decompose(command)
        tasks = decomposition.get("tasks", [])
        replay_existing_tasks = False

        if decomposition.get("intent") == "execute_pending_tasks":
            tasks = [
                dict(task)
                for task in self.state.running_tasks
                if str(task.get("status", "pending")).strip().lower() in {"pending", "blocked"}
            ]
            decomposition["tasks"] = tasks
            decomposition["task_count"] = len(tasks)
            replay_existing_tasks = True

        pipeline_trace = {
            "trace_id": str(uuid.uuid4()),
            "command": command,
            "pipeline": [],
            "final": {},
        }

        # Step 1 — ExecutiveBrain / TaskDecomposer
        pipeline_trace["pipeline"].append({
            "step": 1,
            "name": "ExecutiveBrain → TaskDecomposer",
            "status": "completed" if tasks else "no_match",
            "output": {
                "intent": decomposition["intent"],
                "task_count": decomposition["task_count"],
                "tasks": [
                    {
                        "id": t.get("id"),
                        "description": t.get("description") or t.get("target") or t.get("id"),
                    }
                    for t in tasks
                ],
            },
        })

        if not tasks:
            pipeline_trace["final"] = {
                "accepted": False,
                "reason": "no_pending_tasks" if decomposition["intent"] == "execute_pending_tasks" else "no_tasks_generated",
                "technical_reason": (
                    "لا توجد مهام معلّقة قابلة لإعادة التنفيذ في الحالة التنفيذية."
                    if decomposition["intent"] == "execute_pending_tasks"
                    else "TaskDecomposer لم يولّد مهاماً قابلة للتنفيذ لهذه النية."
                ),
                "intent": decomposition["intent"],
            }
            return pipeline_trace

        # AEX-1 external effects never execute from a plain command. They create
        # an explicit approval request and return a complete trace instead.
        external_intents = {"open_branch", "open_pull_request", "deploy_railway"}
        if decomposition["intent"] in external_intents:
            approval_id = None
            if self.approvals is not None:
                approval_id = self.approvals.request(
                    action="publish" if decomposition["intent"] == "deploy_railway" else "external",
                    description=f"AEX-1 approval required: {command[:240]}",
                    requested_by=requested_by,
                    context={"intent": decomposition["intent"], "command": command},
                )
            pipeline_trace["pipeline"].append({
                "step": 2,
                "name": "ApprovalGate",
                "status": "pending",
                "output": {
                    "approval_id": approval_id,
                    "intent": decomposition["intent"],
                    "reason": "explicit_approval_required",
                },
            })
            pipeline_trace["final"] = {
                "accepted": False,
                "reason": "explicit_approval_required",
                "technical_reason": "هذا الإجراء يغيّر حالة GitHub أو Railway، ولذلك لا يُنفّذ قبل موافقة صريحة.",
                "intent": decomposition["intent"],
                "approval_id": approval_id,
                "completed": 0,
                "failed": 0,
                "blocked": 1,
                "results": [{
                    "task_id": tasks[0].get("id"),
                    "status": "blocked",
                    "reason": "explicit_approval_required",
                    "approval_id": approval_id,
                }],
            }
            return pipeline_trace

        # Steps 2–5 — PlanValidator → Scheduler → ToolDispatcher → FileExecutor (via execute_task)
        result = self.execute_task(
            tasks,
            guardian=guardian,
            request_type=request_type,
            intent=decomposition["intent"],
            requested_by=requested_by,
            register_tasks=not replay_existing_tasks,
        )

        # Step 2 — PlanValidator
        pipeline_trace["pipeline"].append({
            "step": 2,
            "name": "PlanValidator",
            "status": "passed" if result["validation"]["valid"] else "blocked",
            "output": result["validation"],
        })

        # Step 3 — Scheduler
        pipeline_trace["pipeline"].append({
            "step": 3,
            "name": "Scheduler",
            "status": "accepted" if result["schedule"].get("accepted") else "rejected",
            "output": result["schedule"].get("summary", {}),
        })

        # Step 4 — ToolDispatcher
        exec_results = result["execution"]["results"]
        governance = [
            item.get("governance", {})
            for item in exec_results
            if isinstance(item, dict) and isinstance(item.get("governance"), dict)
        ]
        auth_events = [g.get("execution_authorization", {}) for g in governance if isinstance(g, dict)]
        boundary_events = [g.get("execution_boundary", {}) for g in governance if isinstance(g, dict)]
        pipeline_trace["pipeline"].append({
            "step": 4,
            "name": "ToolDispatcher",
            "status": "completed" if result["execution"]["completed"] == len(tasks) else "partial",
            "output": {
                "completed": result["execution"]["completed"],
                "failed": result["execution"]["failed"],
                "blocked": result["execution"]["blocked"],
                "decisions": [
                    {
                        "decision": (g.get("dispatcher") or {}).get("decision"),
                        "reason": (g.get("dispatcher") or {}).get("reason"),
                    }
                    for g in governance
                    if isinstance(g, dict)
                ],
            },
        })

        pipeline_trace["pipeline"].append({
            "step": 5,
            "name": "ExecutionBoundary",
            "status": "completed" if boundary_events else "unavailable",
            "output": {
                "events": boundary_events,
            },
        })

        pipeline_trace["pipeline"].append({
            "step": 6,
            "name": "ExecutionAuthorization",
            "status": "completed" if auth_events else "unavailable",
            "output": {
                "events": auth_events,
            },
        })

        pipeline_trace["pipeline"].append({
            "step": 7,
            "name": "FileExecutor",
            "status": "completed" if result["execution"]["completed"] == len(tasks) else "partial",
            "output": {
                "files": [
                    r.get("relative_path", r.get("task_id")) for r in exec_results
                    if r.get("status") == "completed"
                ],
            },
        })

        pipeline_trace["final"] = {
            "accepted": result["accepted"],
            "reason": None if result["accepted"] else "execution_blocked_or_failed",
            "technical_reason": None if result["accepted"] else "راجع نتائج الحوكمة لكل مهمة لمعرفة سبب الحظر أو الفشل.",
            "tasks_queued": result["tasks_queued"],
            "completed": result["execution"]["completed"],
            "failed": result["execution"]["failed"],
            "results": exec_results,
            "files_created": [
                r.get("relative_path") for r in exec_results
                if r.get("status") == "completed"
                and str(r.get("action", "")).strip().lower() in {"write", "create", "append"}
            ],
            "preview_path": (
                "09_Assets/runtime_workspace/home/index.html"
                if decomposition["intent"] == "build_homepage"
                else next(
                    (
                        r.get("relative_path")
                        for r in exec_results
                        if r.get("status") == "completed"
                        and str(r.get("relative_path", "")).endswith("index.html")
                    ),
                    None,
                )
                if decomposition["intent"] == "build_generic"
                else None
            ),
        }

        return pipeline_trace

    # ── Decision & Approval helpers (continued) ───────────────────────────────

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
