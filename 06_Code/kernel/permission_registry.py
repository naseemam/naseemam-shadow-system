"""
permission_registry.py
======================
سجل التمكين التشغيلي لأمير.

القدرة تصف ما يستطيع أمير فعله، وهذه البطاقات توثق التمكين والنطاق التقني
والتعطيل الصريح. السجل ليس بوابة موافقة مؤسس ولا يحق له إنشاء بوابات جديدة.

قاعدة السلطة العليا موجودة فقط في ``kernel.ameer_authority``. لذلك:
- القدرة الجديدة المملوكة لأمير تكون مفعلة وممنوحة تشغيلياً افتراضياً.
- حالة ``requires_approval`` القديمة لا تنشئ موافقة مؤسس؛ تُرحّل إلى granted.
- التعطيل الصريح ``enabled=False`` يبقى حاجزاً تقنياً مقصوداً وقابلاً للتدقيق.
- البوابات السيادية وحدها تحدد متى ينتظر أمير قرار المؤسس.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


_PERMISSIONS_FILENAME = "permissions.json"

# Legacy values are retained for compatibility with persisted data, but new
# operational cards are created as granted under delegated authority.
PERMISSION_STATUSES = {"granted", "not_granted", "requires_approval"}
_DELEGATED_SCOPE = "delegated_operational_authority"
_DELEGATED_BY = "ameer_sovereign_authority"


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class PermissionRegistry:
    """Persistent operational-enablement registry; not a founder approval gate."""

    def __init__(self, workspace_root: str | Path) -> None:
        self._root = Path(workspace_root).resolve()
        self._ameer_dir = self._root / ".ameer"
        self._path = self._ameer_dir / _PERMISSIONS_FILENAME
        self._data: Dict[str, Any] = {"permissions": [], "audit_log": []}
        self._load()
        self.normalize_delegated_authority()

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

    def normalize_delegated_authority(self) -> int:
        """Migrate legacy approval-based cards to delegated operational authority.

        Explicitly disabled cards remain disabled. Expiry metadata is retained,
        although normal delegated cards are permanent. Returns number migrated.
        """
        changed = 0
        for card in self._data.get("permissions", []):
            if not card.get("owned", True):
                continue
            status = card.get("permission_status", "not_granted")
            if status in {"not_granted", "requires_approval"}:
                old_status = status
                card["permission_status"] = "granted"
                if not card.get("scope"):
                    card["scope"] = _DELEGATED_SCOPE
                card["granted_by"] = card.get("granted_by") or _DELEGATED_BY
                card["granted_at"] = card.get("granted_at") or _now_iso()
                card["updated_at"] = _now_iso()
                self._audit(
                    card["permission_id"],
                    "delegated_authority_migration",
                    f"legacy_status={old_status}; founder approval gates are controlled only by ameer_authority",
                )
                changed += 1
        if changed:
            self._save()
        return changed

    def ensure(self, capability_id: str) -> str:
        """Ensure an owned capability has an autonomous operational card."""
        existing = self._find_by_capability(capability_id)
        if existing:
            return existing["permission_id"]

        now = _now_iso()
        card: Dict[str, Any] = {
            "permission_id": str(uuid.uuid4()),
            "capability_id": capability_id,
            "owned": True,
            "enabled": True,
            "permission_status": "granted",
            "scope": _DELEGATED_SCOPE,
            "granted_by": _DELEGATED_BY,
            "granted_at": now,
            "expires_at": None,
            "created_at": now,
            "updated_at": now,
        }
        self._data["permissions"].append(card)
        self._audit(
            card["permission_id"],
            "created_delegated",
            "Operational authority inherited from Ameer sovereign authority policy",
        )
        self._save()
        return card["permission_id"]

    def grant(
        self,
        capability_id: str,
        scope: str = _DELEGATED_SCOPE,
        granted_by: str = _DELEGATED_BY,
        expires_at: Optional[str] = None,
    ) -> str:
        if not capability_id:
            raise ValueError("capability_id must not be empty")

        card = self._find_by_capability(capability_id)
        if card is None:
            self.ensure(capability_id)
            card = self._find_by_capability(capability_id)

        card["permission_status"] = "granted"
        card["scope"] = scope or _DELEGATED_SCOPE
        card["granted_by"] = granted_by or _DELEGATED_BY
        card["granted_at"] = _now_iso()
        card["expires_at"] = expires_at
        card["enabled"] = True
        card["owned"] = True
        card["updated_at"] = _now_iso()
        self._audit(
            card["permission_id"],
            "granted",
            f"scope={card['scope']}, granted_by={card['granted_by']}, expires_at={expires_at}",
        )
        self._save()
        return card["permission_id"]

    def revoke(
        self,
        permission_id: str,
        reason: str = "",
        revoked_by: str = "founder",
    ) -> None:
        """Explicitly disable a capability card; does not create an approval loop."""
        card = self._find(permission_id)
        if card is None:
            raise KeyError(f"Permission '{permission_id}' not found")
        card["enabled"] = False
        card["updated_at"] = _now_iso()
        self._audit(
            permission_id,
            "explicitly_disabled",
            f"disabled_by={revoked_by}, reason={reason}",
        )
        self._save()

    def set_requires_approval(self, capability_id: str, scope: str = "") -> str:
        """Compatibility shim: capability-level founder gates are no longer valid.

        Historical callers may still call this method. We keep the capability
        granted and record that the attempted extra gate was ignored.
        """
        card = self._find_by_capability(capability_id)
        if card is None:
            self.ensure(capability_id)
            card = self._find_by_capability(capability_id)

        card["permission_status"] = "granted"
        card["scope"] = scope or card.get("scope") or _DELEGATED_SCOPE
        card["enabled"] = True
        card["updated_at"] = _now_iso()
        self._audit(
            card["permission_id"],
            "legacy_requires_approval_ignored",
            "Only kernel.ameer_authority may require Founder approval",
        )
        self._save()
        return card["permission_id"]

    def disable(self, capability_id: str, reason: str = "") -> None:
        card = self._find_by_capability(capability_id)
        if card is None:
            raise KeyError(f"No permission card for capability '{capability_id}'")
        card["enabled"] = False
        card["updated_at"] = _now_iso()
        self._audit(card["permission_id"], "disabled", reason)
        self._save()

    def enable(self, capability_id: str, reason: str = "") -> None:
        card = self._find_by_capability(capability_id)
        if card is None:
            self.ensure(capability_id)
            card = self._find_by_capability(capability_id)
        card["enabled"] = True
        card["permission_status"] = "granted"
        card["updated_at"] = _now_iso()
        self._audit(card["permission_id"], "enabled", reason)
        self._save()

    def get(self, permission_id: str) -> Optional[Dict[str, Any]]:
        return self._find(permission_id)

    def get_for_capability(self, capability_id: str) -> Optional[Dict[str, Any]]:
        card = self._find_by_capability(capability_id)
        if card is None:
            return None
        result = dict(card)
        result["is_expired"] = self._is_expired(card)
        return result

    def is_permitted(self, capability_id: str) -> bool:
        """Technical execution check, not a founder-approval decision."""
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
            if p.get("permission_status") == "granted"
            and p.get("enabled", False)
            and not self._is_expired(p)
        ]

    def audit_log(self) -> List[Dict[str, Any]]:
        return list(self._data["audit_log"])

    def snapshot(self) -> Dict[str, Any]:
        counts = {s: 0 for s in PERMISSION_STATUSES}
        for p in self._data["permissions"]:
            s = p.get("permission_status", "granted")
            counts[s] = counts.get(s, 0) + 1
        return {
            "total": len(self._data["permissions"]),
            "by_status": counts,
            "enabled": len([p for p in self._data["permissions"] if p.get("enabled", False)]),
            "audit_log_entries": len(self._data["audit_log"]),
            "policy": "delegated_autonomy; founder gates live only in ameer_authority",
        }
