"""
approval_gate.py
================
Approval Gate — بوابة الموافقة التنفيذية.

أي إجراء عالي التأثير يجب أن يمر بهذه البوابة قبل التنفيذ.
المؤسسة هي صاحبة القرار النهائي — أمير لا ينفّذ إجراءات حساسة دون موافقة.

الأنواع المدعومة من الطلبات:
- "publish"  — نشر محتوى أو نشر إنتاجي
- "external" — استدعاء API خارجي أو إرسال بيانات
- "financial"— أي عملية مالية
- "config"   — تغيير إعدادات النظام الخارجية
- "other"    — أي طلب حساس آخر

عمليات المستودع الداخلية مثل القراءة والكتابة والاختبار والدمج والحذف داخل النطاق
المصرح بها تقع تحت سلطة أمير ولا تتطلب موافقة المؤسس لكل خطوة.

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
        "action": "publish|deploy|external|financial|config|other",
        "description": "...",
        "requested_by": "...",
        "status": "pending|approved|rejected|expired",
        "approved_by": null,
        "rejection_reason": null,
        "requested_at": "<iso>",
        "resolved_at": "<iso|null>",
    }
    """

    VALID_ACTIONS = {"publish", "deploy", "external", "financial", "config", "other"}
    VALID_STATUSES = {"pending", "approved", "rejected", "expired"}

    # الأفعال التي تحتاج موافقة المؤسس دائمًا
    HIGH_RISK_ACTIONS = {"publish", "deploy", "external", "financial"}

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

    def requires_approval(self, action: str) -> bool:
        """يُعيد True إذا كان الإجراء يحتاج موافقة المؤسسة."""
        return action in self.HIGH_RISK_ACTIONS

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
        if action not in self.VALID_ACTIONS:
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
