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

        # Component registry
        self.state: ExecutiveStateManager = ExecutiveStateManager(self._root)
        self.workspace: WorkspaceAwareness = WorkspaceAwareness(self._root)
        self.session: SessionContext = SessionContext()
        self.founder: FounderProfile = FounderProfile(self._root)

    # ── Startup ───────────────────────────────────────────────────────────────

    def boot(self) -> dict:
        """
        تهيئة كاملة عند الـ startup.
        يُعيد تقرير صحة النظام.
        """
        self._health = {}
        errors = []

        # 1. State Manager
        try:
            self.state.mark_session_start()
            self._health["state_manager"] = "ok"
        except Exception as exc:
            self._health["state_manager"] = f"error: {exc}"
            errors.append("state_manager")

        # 2. Founder Profile
        try:
            self.founder.load()
            # Cache founder context into state
            founder_ctx = {"loaded": True, "sections": list(self.founder.sections.keys())}
            self.state.set_founder_context(founder_ctx)
            self._health["founder_profile"] = "ok"
        except Exception as exc:
            self._health["founder_profile"] = f"error: {exc}"
            errors.append("founder_profile")

        # 3. Workspace Awareness
        try:
            scan = self.workspace.scan()
            summary = self.workspace.build_executive_summary(scan)
            self.state.set_workspace_summary(summary)
            self._health["workspace_awareness"] = "ok"
        except Exception as exc:
            self._health["workspace_awareness"] = f"error: {exc}"
            errors.append("workspace_awareness")
            summary = ""

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

        return {
            "status": overall,
            "booted_at": _now_iso(),
            "components": self._health,
            "errors": errors,
            "workspace_summary": summary if "workspace_awareness" not in errors else "",
        }

    # ── Per-Request Lifecycle ─────────────────────────────────────────────────

    def before_request(self, query: str) -> dict:
        """
        يُعيد السياق الكامل المطلوب قبل معالجة كل طلب.
        يُدار داخل ameer_server.py قبل استدعاء Executive Brain.
        """
        if not self._initialized:
            self.boot()

        # Record user turn in session context
        self.session.add_user_message(query)

        return {
            "conversation_context": self.session.build_context_block(),
            "founder_context": self.founder.build_context_block(),
            "workspace_summary": self.state.workspace_summary,
            "pending_approvals": self.state.pending_approvals,
            "session_count": self.state.session_count,
            "is_follow_up": self.session.is_follow_up(),
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
