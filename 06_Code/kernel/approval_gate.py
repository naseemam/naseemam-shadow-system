"""
approval_gate.py
================
Approval Gate — بوابة الموافقة التنفيذية.

تُستخدم هذه البوابة فقط قبل إنشاء أصل رقمي مستقل جديد. يملك أمير التنفيذ
الكامل داخل الأصول القائمة؛ ولا يحجز النشر أو البريد أو الحذف أو النشر الإنتاجي
أو أي أثر خارجي قائم بذاته.

بوابات الموافقة الذاتية الوحيدة هي:
- "create_site"       — إنشاء موقع مستقل جديد
- "create_program"    — إنشاء برنامج مستقل جديد
- "create_system"     — إنشاء نظام مستقل جديد
- "create_repository" — إنشاء مستودع مستقل جديد

تظل أنواع السجل القديمة مثل "publish" و"external" و"financial" صالحة
للتوثيق أو الطلب اليدوي، لكنها لا تعد موافقات مطلوبة تلقائيًا.

كل طلب موافقة له حالة:
- "pending"  — ينتظر رد المؤسسة
- "approved" — وافقت عليه المؤسسة
- "rejected" — رفضته المؤسسة
- "expired"  — انتهت مهلته دون رد

يُخزَّن في .ameer/approvals.json لضمان البقاء عبر الجلسات.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from kernel.ameer_authority import ROOT_ASSET_ACTIONS, canonical_creation_action, requires_founder_approval


_APPROVALS_FILENAME = "approvals.json"
_MAX_STORED = 100


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class ApprovalGate:
    """
    بوابة الموافقة التنفيذية.

    مثال على الاستخدام:
    -------------------
    gate = ApprovalGate(workspace_root)
    request_id = gate.request(
        action="delete",
        description="حذف ملف السجل القديم",
        requested_by="executive_brain",
    )
    # ... (في وقت لاحق عبر API) ...
    gate.approve(request_id, approved_by="naseem")
    can_proceed = gate.is_approved(request_id)  # True

    كل طلب له بنية:
    {
        "id": "<uuid>",
        "action": "create_site|create_program|create_system|create_repository|...",
        "description": "...",
        "requested_by": "...",
        "status": "pending|approved|rejected|expired",
        "approved_by": null,
        "rejection_reason": null,
        "requested_at": "<iso>",
        "resolved_at": "<iso|null>",
    }
    """

    # تبقى الأنواع القديمة قابلة للتسجيل حتى لا ينكسر سجل الموافقات السابق،
    # لكن المصدر المركزي يقرر وحده ما الذي يحتاج موافقة تلقائية.
    VALID_ACTIONS = set(ROOT_ASSET_ACTIONS) | {"delete", "publish", "deploy", "rollback", "external", "financial", "config", "other"}
    VALID_STATUSES = {"pending", "approved", "rejected", "expired"}
    HIGH_RISK_ACTIONS = set(ROOT_ASSET_ACTIONS)

    def __init__(self, workspace_root: str | Path) -> None:
        self._root = Path(workspace_root).resolve()
        self._path = self._root / ".ameer" / _APPROVALS_FILENAME
        self._approvals: List[Dict[str, Any]] = []
        self._load()

    # ── Persistence ───────────────────────────────────────────────────────────

    def _load(self) -> None:
        if self._path.exists():
            try:
                raw = self._path.read_text(encoding="utf-8")
                loaded = json.loads(raw)
                if isinstance(loaded, list):
                    self._approvals = loaded
                    return
            except Exception:
                pass
        self._approvals = []

    def _save(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(
                json.dumps(self._approvals, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
            pass

    # ── Core API ──────────────────────────────────────────────────────────────

    def requires_approval(self, action: str, context: Optional[Dict[str, Any]] = None) -> bool:
        """يُعيد True فقط لإنشاء موقع أو برنامج أو نظام أو مستودع مستقل جديد."""
        return requires_founder_approval(action, context)

    def request(
        self,
        action: str,
        description: str,
        requested_by: str = "executive_brain",
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        يُنشئ طلب موافقة جديداً ويُعيد معرّفه.

        :param action: نوع الإجراء
        :param description: وصف مختصر للإجراء المطلوب
        :param requested_by: الجهة الطالبة
        :param context: بيانات إضافية (اختياري)
        :returns: approval_id (UUID string)
        """
        if not description or not description.strip():
            raise ValueError("description is required")
        canonical_action = canonical_creation_action(action, context)
        if canonical_action:
            action = canonical_action
        elif action not in self.VALID_ACTIONS:
            action = "other"

        approval: Dict[str, Any] = {
            "id": str(uuid.uuid4()),
            "action": action,
            "description": description.strip(),
            "requested_by": (requested_by or "unknown").strip(),
            "context": context or {},
            "status": "pending",
            "approved_by": None,
            "rejected_by": None,
            "rejection_reason": None,
            "requested_at": _now_iso(),
            "resolved_at": None,
        }
        self._approvals.append(approval)
        if len(self._approvals) > _MAX_STORED:
            self._approvals = self._approvals[-_MAX_STORED:]
        self._save()
        return approval["id"]

    def approve(self, approval_id: str, approved_by: str = "naseem") -> bool:
        """
        يُسجّل موافقة المؤسسة على طلب.
        :returns: True إذا وُجد الطلب وحُدِّث.
        """
        for approval in self._approvals:
            if approval["id"] == approval_id and approval["status"] == "pending":
                approval["status"] = "approved"
                approval["approved_by"] = (approved_by or "naseem").strip()
                approval["resolved_at"] = _now_iso()
                self._save()
                return True
        return False

    def reject(self, approval_id: str, reason: str = "", rejected_by: str = "naseem") -> bool:
        """
        يُسجّل رفض المؤسسة لطلب.
        :returns: True إذا وُجد الطلب وحُدِّث.
        """
        for approval in self._approvals:
            if approval["id"] == approval_id and approval["status"] == "pending":
                approval["status"] = "rejected"
                approval["rejected_by"] = (rejected_by or "naseem").strip()
                approval["rejection_reason"] = (reason or "").strip()
                approval["resolved_at"] = _now_iso()
                self._save()
                return True
        return False

    def is_approved(self, approval_id: str) -> bool:
        """يُعيد True إذا كان الطلب معتمداً."""
        for approval in self._approvals:
            if approval["id"] == approval_id:
                return approval["status"] == "approved"
        return False

    def get(self, approval_id: str) -> Optional[Dict[str, Any]]:
        """يُعيد طلباً بمعرّفه، أو None."""
        for approval in self._approvals:
            if approval["id"] == approval_id:
                return dict(approval)
        return None

    def pending(self) -> List[Dict[str, Any]]:
        """يُعيد الطلبات المعلّقة (pending)."""
        return [dict(a) for a in self._approvals if a.get("status") == "pending"]

    def recent(self, limit: int = 10) -> List[Dict[str, Any]]:
        """يُعيد آخر N طلبات (الأحدث أولاً)."""
        return [dict(a) for a in reversed(self._approvals[-limit:])]

    def snapshot(self) -> Dict[str, Any]:
        """ملخص حالة بوابة الموافقة."""
        return {
            "total": len(self._approvals),
            "pending": len(self.pending()),
            "recent": self.recent(5),
        }
