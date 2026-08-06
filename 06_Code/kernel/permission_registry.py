"""
permission_registry.py
======================
Permission Registry — سجل الصلاحيات التنفيذي.

الفصل الجوهري: القدرة ≠ الصلاحية
-----------------------------------
- القدرة: ما يعرفه أمير ويستطيع فعله (مخزنة في CapabilityRegistry)
- الصلاحية: هل يُسمح له بتشغيل هذه القدرة على نظام أو تطبيق معين؟

لكل قدرة بطاقة صلاحية (Permission Card) تحتوي على:
    capability_id     — مرتبط ببطاقة القدرة
    owned             — هل يملك أمير هذه القدرة؟
    enabled           — هل هي مفعلة حالياً؟
    permission_status — Granted / NotGranted / RequiresApproval
    scope             — نطاق التنفيذ المسموح به
    granted_by        — المؤسس
    granted_at        — تاريخ وقت المنح
    expires_at        — صلاحية مؤقتة أم دائمة (None = دائمة)

مبدأ الحوكمة:
    "القدرات دائمة ما لم يقرر المؤسس إزالتها.
     أما التنفيذ العملي للقدرات على الأنظمة والتطبيقات
     فيخضع دائماً لصلاحيات مستقلة وموافقة المؤسس."

يُخزَّن في .ameer/permissions.json لضمان البقاء عبر الجلسات.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


_PERMISSIONS_FILENAME = "permissions.json"

PERMISSION_STATUSES = {"granted", "not_granted", "requires_approval"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class PermissionRegistry:
    """
    سجل صلاحيات تنفيذ القدرات.

    واجهة الاستخدام:
    ----------------
    registry = PermissionRegistry(workspace_root)

    # منح صلاحية
    perm_id = registry.grant(
        capability_id="<uuid>",
        scope="read-only",
        granted_by="Naseem",
    )

    # سحب صلاحية
    registry.revoke(perm_id, reason="Audit in progress")

    # فحص الصلاحية الحالية
    card = registry.get_for_capability(capability_id)
    """

    def __init__(self, workspace_root: str | Path) -> None:
        self._root = Path(workspace_root).resolve()
        self._ameer_dir = self._root / ".ameer"
        self._path = self._ameer_dir / _PERMISSIONS_FILENAME
        self._data: Dict[str, Any] = {"permissions": [], "audit_log": []}
        self._load()

    # ── Persistence ───────────────────────────────────────────────────────────

    def _load(self) -> None:
        if self._path.exists():
            try:
                raw = self._path.read_text(encoding="utf-8")
                self._data = json.loads(raw)
                if "permissions" not in self._data:
                    self._data["permissions"] = []
                if "audit_log" not in self._data:
                    self._data["audit_log"] = []
            except (json.JSONDecodeError, OSError):
                self._data = {"permissions": [], "audit_log": []}

    def _save(self) -> None:
        self._ameer_dir.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(self._data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _find(self, permission_id: str) -> Optional[Dict[str, Any]]:
        for p in self._data["permissions"]:
            if p["permission_id"] == permission_id:
                return p
        return None

    def _find_by_capability(self, capability_id: str) -> Optional[Dict[str, Any]]:
        for p in self._data["permissions"]:
            if p["capability_id"] == capability_id:
                return p
        return None

    def _audit(self, permission_id: str, action: str, detail: str) -> None:
        self._data["audit_log"].append(
            {
                "timestamp": _now_iso(),
                "permission_id": permission_id,
                "action": action,
                "detail": detail,
            }
        )

    def _is_expired(self, card: Dict[str, Any]) -> bool:
        expires_at = card.get("expires_at")
        if not expires_at:
            return False
        try:
            expiry = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            return datetime.now(timezone.utc) > expiry
        except (ValueError, TypeError):
            return False

    # ── Public API ────────────────────────────────────────────────────────────

    def ensure(self, capability_id: str) -> str:
        """
        يضمن وجود بطاقة صلاحية للقدرة (تُنشأ بحالة not_granted إذا لم تكن موجودة).
        يُعيد permission_id.
        """
        existing = self._find_by_capability(capability_id)
        if existing:
            return existing["permission_id"]

        card: Dict[str, Any] = {
            "permission_id": str(uuid.uuid4()),
            "capability_id": capability_id,
            "owned": True,
            "enabled": True,
            "permission_status": "not_granted",
            "scope": "",
            "granted_by": None,
            "granted_at": None,
            "expires_at": None,
            "created_at": _now_iso(),
            "updated_at": _now_iso(),
        }
        self._data["permissions"].append(card)
        self._audit(card["permission_id"], "created", "Permission card initialised as not_granted")
        self._save()
        return card["permission_id"]

    def grant(
        self,
        capability_id: str,
        scope: str,
        granted_by: str = "founder",
        expires_at: Optional[str] = None,
    ) -> str:
        """
        منح صلاحية لقدرة معينة.

        يُنشئ بطاقة الصلاحية إذا لم تكن موجودة.
        يُعيد permission_id.
        """
        if not capability_id:
            raise ValueError("capability_id must not be empty")

        card = self._find_by_capability(capability_id)
        if card is None:
            self.ensure(capability_id)
            card = self._find_by_capability(capability_id)

        card["permission_status"] = "granted"
        card["scope"] = scope
        card["granted_by"] = granted_by
        card["granted_at"] = _now_iso()
        card["expires_at"] = expires_at
        card["enabled"] = True
        card["updated_at"] = _now_iso()

        self._audit(
            card["permission_id"],
            "granted",
            f"scope={scope}, granted_by={granted_by}, expires_at={expires_at}",
        )
        self._save()
        return card["permission_id"]

    def revoke(
        self,
        permission_id: str,
        reason: str = "",
        revoked_by: str = "founder",
    ) -> None:
        """سحب صلاحية — يُعيد الحالة إلى not_granted."""
        card = self._find(permission_id)
        if card is None:
            raise KeyError(f"Permission '{permission_id}' not found")

        card["permission_status"] = "not_granted"
        card["scope"] = ""
        card["granted_by"] = None
        card["granted_at"] = None
        card["expires_at"] = None
        card["updated_at"] = _now_iso()

        self._audit(
            permission_id,
            "revoked",
            f"revoked_by={revoked_by}, reason={reason}",
        )
        self._save()

    def set_requires_approval(self, capability_id: str, scope: str = "") -> str:
        """
        تعيين صلاحية بحالة requires_approval — تحتاج موافقة في كل تنفيذ.
        يُعيد permission_id.
        """
        card = self._find_by_capability(capability_id)
        if card is None:
            self.ensure(capability_id)
            card = self._find_by_capability(capability_id)

        card["permission_status"] = "requires_approval"
        card["scope"] = scope
        card["updated_at"] = _now_iso()

        self._audit(card["permission_id"], "requires_approval_set", f"scope={scope}")
        self._save()
        return card["permission_id"]

    def disable(self, capability_id: str, reason: str = "") -> None:
        """تعطيل قدرة (enabled=False) دون تغيير حالة الصلاحية."""
        card = self._find_by_capability(capability_id)
        if card is None:
            raise KeyError(f"No permission card for capability '{capability_id}'")
        card["enabled"] = False
        card["updated_at"] = _now_iso()
        self._audit(card["permission_id"], "disabled", reason)
        self._save()

    def enable(self, capability_id: str, reason: str = "") -> None:
        """إعادة تفعيل قدرة (enabled=True)."""
        card = self._find_by_capability(capability_id)
        if card is None:
            raise KeyError(f"No permission card for capability '{capability_id}'")
        card["enabled"] = True
        card["updated_at"] = _now_iso()
        self._audit(card["permission_id"], "enabled", reason)
        self._save()

    def get(self, permission_id: str) -> Optional[Dict[str, Any]]:
        """إرجاع بطاقة الصلاحية بالمعرف."""
        return self._find(permission_id)

    def get_for_capability(self, capability_id: str) -> Optional[Dict[str, Any]]:
        """إرجاع بطاقة الصلاحية لقدرة معينة."""
        card = self._find_by_capability(capability_id)
        if card is None:
            return None
        # Annotate expiry status inline (non-mutating view)
        result = dict(card)
        result["is_expired"] = self._is_expired(card)
        return result

    def is_permitted(self, capability_id: str) -> bool:
        """
        فحص سريع: هل يملك أمير صلاحية تنفيذ هذه القدرة الآن؟

        True فقط إذا:
        - owned=True
        - enabled=True
        - permission_status="granted"
        - لم تنته الصلاحية
        """
        card = self._find_by_capability(capability_id)
        if card is None:
            return False
        return (
            card.get("owned", False)
            and card.get("enabled", False)
            and card.get("permission_status") == "granted"
            and not self._is_expired(card)
        )

    def list_all(self) -> List[Dict[str, Any]]:
        return list(self._data["permissions"])

    def list_granted(self) -> List[Dict[str, Any]]:
        return [
            p for p in self._data["permissions"]
            if p.get("permission_status") == "granted" and not self._is_expired(p)
        ]

    def audit_log(self) -> List[Dict[str, Any]]:
        return list(self._data["audit_log"])

    def snapshot(self) -> Dict[str, Any]:
        counts = {s: 0 for s in PERMISSION_STATUSES}
        for p in self._data["permissions"]:
            s = p.get("permission_status", "not_granted")
            counts[s] = counts.get(s, 0) + 1
        return {
            "total": len(self._data["permissions"]),
            "by_status": counts,
            "audit_log_entries": len(self._data["audit_log"]),
        }
