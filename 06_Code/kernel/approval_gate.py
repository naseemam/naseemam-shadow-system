"""
approval_gate.py
================
بوابة الموافقة السيادية لأمير.

هذه البوابة لا تملك حق اختراع موافقات جديدة. المصدر الوحيد للحكم هو
kernel.ameer_authority، وتُفتح الموافقة فقط عند واحدة من البوابات السيادية:

1. إنشاء أصل رقمي جذري جديد: موقع/برنامج/نظام/مستودع.
2. الاعتماد النهائي قبل إدخال ذلك الأصل الجديد إلى الإنتاج.
3. تنفيذ نقل أو دفع أو حركة مالية فعلية.

كل تطوير وتشغيل وتعديل ونشر داخل أصل قائم مستقل ولا يفتح موافقة مؤسس.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from kernel.ameer_authority import (
    SOVEREIGN_ACTIONS,
    canonical_sovereign_action,
    requires_founder_approval,
)


_APPROVALS_FILENAME = "approvals.json"
_MAX_STORED = 100


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class ApprovalGate:
    """Persistent founder-decision store for sovereign gates only."""

    # Legacy action names remain storable for historical records/manual notes,
    # but they do not become automatic gates unless ameer_authority says so.
    VALID_ACTIONS = set(SOVEREIGN_ACTIONS) | {
        "delete", "publish", "deploy", "rollback", "external", "financial", "config", "other"
    }
    VALID_STATUSES = {"pending", "approved", "rejected", "expired"}
    HIGH_RISK_ACTIONS = set(SOVEREIGN_ACTIONS)

    def __init__(self, workspace_root: str | Path) -> None:
        self._root = Path(workspace_root).resolve()
        self._path = self._root / ".ameer" / _APPROVALS_FILENAME
        self._approvals: List[Dict[str, Any]] = []
        self._load()

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

    def requires_approval(self, action: str, context: Optional[Dict[str, Any]] = None) -> bool:
        """True only when the central sovereign policy identifies a founder gate."""
        return requires_founder_approval(action, context)

    def request(
        self,
        action: str,
        description: str,
        requested_by: str = "executive_brain",
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        if not description or not description.strip():
            raise ValueError("description is required")

        canonical_action = canonical_sovereign_action(action, context)
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
        for approval in self._approvals:
            if approval["id"] == approval_id and approval["status"] == "pending":
                approval["status"] = "approved"
                approval["approved_by"] = (approved_by or "naseem").strip()
                approval["resolved_at"] = _now_iso()
                self._save()
                return True
        return False

    def reject(self, approval_id: str, reason: str = "", rejected_by: str = "naseem") -> bool:
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
        for approval in self._approvals:
            if approval["id"] == approval_id:
                return approval["status"] == "approved"
        return False

    def get(self, approval_id: str) -> Optional[Dict[str, Any]]:
        for approval in self._approvals:
            if approval["id"] == approval_id:
                return dict(approval)
        return None

    def pending(self) -> List[Dict[str, Any]]:
        return [dict(a) for a in self._approvals if a.get("status") == "pending"]

    def recent(self, limit: int = 10) -> List[Dict[str, Any]]:
        return [dict(a) for a in reversed(self._approvals[-limit:])]

    def snapshot(self) -> Dict[str, Any]:
        return {
            "total": len(self._approvals),
            "pending": len(self.pending()),
            "recent": self.recent(5),
            "sovereign_actions": list(SOVEREIGN_ACTIONS),
        }
