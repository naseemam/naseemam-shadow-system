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
from context.workspace_awareness import WorkspaceAwareness
from context.session_context import SessionContext
from context.founder_profile import FounderProfile


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
        self.workspace: WorkspaceAwareness = WorkspaceAwareness(self._root)
        self.session: SessionContext = SessionContext()
        self.founder: FounderProfile = FounderProfile(self._root)

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
            "active_projects": self.state.active_projects,
            "running_tasks": self.state.running_tasks,
            "executive_assessment": self.state.executive_assessment,
            "session_count": self.state.session_count,
            "is_follow_up": self.session.is_follow_up(),
            "is_first_turn": is_first_turn,
        }

    def after_request(self, reply: str) -> None:
        """يُسجّل رد أمير في تاريخ المحادثة."""
        if reply:
            self.session.add_assistant_message(reply)

    # ── Health ────────────────────────────────────────────────────────────────

    def health(self) -> dict:
        return {
            "initialized": self._initialized,
            "status": self.state.snapshot().get("runtime_status", "unknown"),
            "session_turns": len(self.session),
            "founder_loaded": self.founder.is_loaded,
            "pending_approvals": len(self.state.pending_approvals),
            "components": self._health,
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
