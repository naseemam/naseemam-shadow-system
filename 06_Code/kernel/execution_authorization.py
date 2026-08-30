"""
execution_authorization.py
===========================
تفويض التنفيذ التشغيلي لأمير.

هذه الطبقة تتحقق من ثلاثة أشياء فقط:
1. أن القدرة موجودة ونشطة.
2. أن المورد غير معطل تقنياً وأن النطاق لا يهرب خارج مساحة النظام.
3. هل العملية نفسها إحدى البوابات السيادية المحددة في ameer_authority؟

الموافقة البشرية ليست خاصية لقدرة أو أداة. لا يمكن لبطاقة Permission أو حارس
آخر اختراع حالة pending. الحالة pending تظهر فقط عندما يقرر المصدر المركزي
``requires_founder_approval`` أن العملية بوابة سيادية.

كل طلب ونتيجة تنفيذ يبقيان مسجلين للتدقيق والتعافي.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from kernel.ameer_authority import canonical_sovereign_action, requires_founder_approval
from kernel.capability_registry import CapabilityRegistry
from kernel.permission_registry import PermissionRegistry


_EXEC_AUTH_FILENAME = "execution_auth.json"
AUTHORIZATION_STATUSES = {"approved", "denied", "pending"}

_FILE_READ_TOOL_NAME = "file.read"
_FILE_READ_ACTION = "read"
_FILE_CREATE_TOOL_NAME = "file.create"
_FILE_CREATE_ACTION = "write"
_SHELL_RUN_TOOL_NAME = "shell.run"
_SHELL_RUN_ACTION = "run"


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def file_read_permission_scope() -> str:
    return json.dumps(
        {
            "tool_name": _FILE_READ_TOOL_NAME,
            "action": _FILE_READ_ACTION,
            "scope_kind": "repository_workspace",
            "scope_root": ".",
        },
        ensure_ascii=False,
        sort_keys=True,
    )


def file_create_permission_scope() -> str:
    return json.dumps(
        {
            "tool_name": _FILE_CREATE_TOOL_NAME,
            "action": _FILE_CREATE_ACTION,
            "scope_kind": "repository_workspace",
            "scope_root": ".",
        },
        ensure_ascii=False,
        sort_keys=True,
    )


def shell_run_permission_scope() -> str:
    return json.dumps(
        {
            "tool_name": _SHELL_RUN_TOOL_NAME,
            "action": _SHELL_RUN_ACTION,
            "scope_kind": "workspace_only",
            "approval_required_for_external_effects": False,
            "founder_gate_source": "kernel.ameer_authority",
        },
        ensure_ascii=False,
        sort_keys=True,
    )


class ExecutionAuthorization:
    """Last execution check, subordinate to Ameer's central sovereign policy."""

    def __init__(
        self,
        workspace_root: str | Path,
        capability_registry: CapabilityRegistry,
        permission_registry: PermissionRegistry,
    ) -> None:
        self._root = Path(workspace_root).resolve()
        self._ameer_dir = self._root / ".ameer"
        self._path = self._ameer_dir / _EXEC_AUTH_FILENAME
        self._caps = capability_registry
        self._perms = permission_registry
        self._data: Dict[str, Any] = {"requests": [], "execution_log": []}
        # Normalize persisted legacy permission cards immediately. This avoids
        # old requires_approval/not_granted values silently reintroducing gates.
        normalize = getattr(self._perms, "normalize_delegated_authority", None)
        if callable(normalize):
            normalize()
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            try:
                raw = self._path.read_text(encoding="utf-8")
                self._data = json.loads(raw)
                if "requests" not in self._data:
                    self._data["requests"] = []
                if "execution_log" not in self._data:
                    self._data["execution_log"] = []
            except (json.JSONDecodeError, OSError):
                self._data = {"requests": [], "execution_log": []}

    def _save(self) -> None:
        self._ameer_dir.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(self._data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _find_request(self, request_id: str) -> Optional[Dict[str, Any]]:
        for request in self._data["requests"]:
            if request["request_id"] == request_id:
                return request
        return None

    def _path_inside_workspace(self, target: Any) -> bool:
        """Technical containment boundary only; it is not an approval gate."""
        if not isinstance(target, str) or not target.strip():
            return False
        candidate = Path(target.strip())
        if not candidate.is_absolute():
            candidate = self._root / candidate
        try:
            resolved = candidate.resolve()
            resolved.relative_to(self._root)
            return True
        except (OSError, RuntimeError, ValueError):
            return False

    def _file_operation_scope_denial_reason(
        self,
        *,
        action: str,
        context: Optional[Dict[str, Any]],
        perm_card: Dict[str, Any],
    ) -> str:
        """Allow Ameer to read/write anywhere in its repository workspace.

        This intentionally includes 06_Code and governance-owned implementation
        files so Ameer can maintain and improve itself. The only technical path
        boundary is escaping the repository root.
        """
        safe_context = context or {}
        action_lower = str(action or "").strip().lower()
        tool_name = str(safe_context.get("tool_name") or "").strip().lower()

        if action_lower == _FILE_READ_ACTION:
            if tool_name and tool_name != _FILE_READ_TOOL_NAME:
                return "file.read action must use tool file.read"
        elif action_lower == _FILE_CREATE_ACTION:
            if tool_name and tool_name != _FILE_CREATE_TOOL_NAME:
                return "file write action must use tool file.create"
        else:
            # Other file actions such as edit/delete/move are operational too;
            # containment is still checked below.
            pass

        target = safe_context.get("target")
        if target in (None, ""):
            return "File operation requires a target inside the repository workspace"
        if not self._path_inside_workspace(target):
            return "File operation target escapes Ameer's repository workspace"
        return ""

    def _ensure_permission_card(
        self,
        *,
        capability_name: str,
        capability_id: str,
        context: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Return a delegated operational card, creating one if needed."""
        tool_name_key = str((context or {}).get("tool_name") or "").strip().lower()
        card = None
        if capability_name == "file_operations" and tool_name_key:
            card = self._perms.get_for_capability(tool_name_key)
            if card is None:
                self._perms.ensure(tool_name_key)
                card = self._perms.get_for_capability(tool_name_key)
        if card is None:
            card = self._perms.get_for_capability(capability_id)
        if card is None:
            self._perms.ensure(capability_id)
            card = self._perms.get_for_capability(capability_id)
        return card or {
            "owned": True,
            "enabled": True,
            "permission_status": "granted",
            "scope": "delegated_operational_authority",
            "is_expired": False,
        }

    def check(
        self,
        capability_name: str,
        action: str,
        context: Optional[Dict[str, Any]] = None,
        requested_by: str = "executive_brain",
    ) -> Dict[str, Any]:
        """Check technical executability and the central sovereign founder gate.

        Rules:
        - Missing/inactive capability: denied for a technical capability reason.
        - Explicitly disabled/unowned capability: denied for a technical reason.
        - New-root creation, final release of that new root asset, or actual
          funds movement: pending Founder decision.
        - Everything else: approved without Founder approval.
        """
        request_id = str(uuid.uuid4())
        now = _now_iso()
        safe_context = context or {}

        cap = self._caps.get_by_name(capability_name)
        if cap is None:
            result = self._make_result(
                request_id,
                "denied",
                capability_name,
                action,
                f"Capability '{capability_name}' is not registered",
                safe_context,
                requested_by,
                now,
            )
            self._persist_request(result)
            return result

        active_statuses = {"core", "extended", "experimental"}
        if cap.get("status") not in active_statuses:
            result = self._make_result(
                request_id,
                "denied",
                capability_name,
                action,
                f"Capability '{capability_name}' has status '{cap.get('status')}' and is not active",
                safe_context,
                requested_by,
                now,
            )
            self._persist_request(result)
            return result

        # Central authority is the only source allowed to produce pending.
        if requires_founder_approval(action, safe_context):
            sovereign_action = canonical_sovereign_action(action, safe_context) or action
            result = self._make_result(
                request_id,
                "pending",
                capability_name,
                action,
                f"Sovereign Founder gate: {sovereign_action}",
                safe_context,
                requested_by,
                now,
            )
            result["sovereign_action"] = sovereign_action
            self._persist_request(result)
            return result

        perm_card = self._ensure_permission_card(
            capability_name=capability_name,
            capability_id=cap["capability_id"],
            context=safe_context,
        )

        if not perm_card.get("owned", True):
            result = self._make_result(
                request_id,
                "denied",
                capability_name,
                action,
                "Capability is explicitly marked as not owned",
                safe_context,
                requested_by,
                now,
            )
            self._persist_request(result)
            return result

        if not perm_card.get("enabled", True):
            result = self._make_result(
                request_id,
                "denied",
                capability_name,
                action,
                "Capability is explicitly disabled in the operational registry",
                safe_context,
                requested_by,
                now,
            )
            self._persist_request(result)
            return result

        # Legacy expiry on a delegated card must not become a hidden founder
        # approval loop. It is treated as a technical configuration failure.
        if perm_card.get("is_expired", False):
            result = self._make_result(
                request_id,
                "denied",
                capability_name,
                action,
                "Operational enablement metadata is expired; refresh configuration",
                safe_context,
                requested_by,
                now,
            )
            self._persist_request(result)
            return result

        # Legacy requires_approval/not_granted values are never allowed to
        # create pending. Normalize them to delegated authority where possible.
        if perm_card.get("permission_status") != "granted":
            try:
                self._perms.grant(
                    perm_card.get("capability_id") or cap["capability_id"],
                    scope=perm_card.get("scope") or "delegated_operational_authority",
                    granted_by="ameer_sovereign_authority",
                )
                perm_card = self._perms.get_for_capability(
                    perm_card.get("capability_id") or cap["capability_id"]
                ) or perm_card
            except Exception:
                pass

        if capability_name == "file_operations":
            denial = self._file_operation_scope_denial_reason(
                action=action,
                context=safe_context,
                perm_card=perm_card,
            )
            if denial:
                result = self._make_result(
                    request_id,
                    "denied",
                    capability_name,
                    action,
                    denial,
                    safe_context,
                    requested_by,
                    now,
                )
                self._persist_request(result)
                return result

        result = self._make_result(
            request_id,
            "approved",
            capability_name,
            action,
            "Delegated executive authority: operational execution approved",
            safe_context,
            requested_by,
            now,
        )
        self._persist_request(result)
        return result

    def _make_result(
        self,
        request_id: str,
        status: str,
        capability_name: str,
        action: str,
        reason: str,
        context: Optional[Dict[str, Any]],
        requested_by: str,
        timestamp: str,
    ) -> Dict[str, Any]:
        return {
            "request_id": request_id,
            "status": status,
            "capability_name": capability_name,
            "action": action,
            "reason": reason,
            "context": context or {},
            "requested_by": requested_by,
            "created_at": timestamp,
            "resolved_at": None,
            "resolved_by": None,
            "execution_recorded": False,
        }

    def _persist_request(self, result: Dict[str, Any]) -> None:
        self._data["requests"].append(result)
        if len(self._data["requests"]) > 200:
            self._data["requests"] = self._data["requests"][-200:]
        self._save()

    def authorize(self, request_id: str, authorized_by: str = "founder") -> None:
        """Founder resolves a pending sovereign-gate request."""
        req = self._find_request(request_id)
        if req is None:
            raise KeyError(f"Authorization request '{request_id}' not found")
        if req["status"] != "pending":
            raise ValueError(
                f"Can only authorize pending requests; current status is '{req['status']}'"
            )
        req["status"] = "approved"
        req["resolved_at"] = _now_iso()
        req["resolved_by"] = authorized_by
        self._save()

    def deny(
        self,
        request_id: str,
        denied_by: str = "founder",
        reason: str = "",
    ) -> None:
        """Founder rejects a pending sovereign-gate request."""
        req = self._find_request(request_id)
        if req is None:
            raise KeyError(f"Authorization request '{request_id}' not found")
        if req["status"] != "pending":
            raise ValueError(
                f"Can only deny pending requests; current status is '{req['status']}'"
            )
        req["status"] = "denied"
        req["resolved_at"] = _now_iso()
        req["resolved_by"] = denied_by
        if reason:
            req["reason"] = reason
        self._save()

    def record_execution(
        self,
        request_id: str,
        outcome: str,
        detail: str = "",
    ) -> None:
        req = self._find_request(request_id)
        if req is None:
            raise KeyError(f"Authorization request '{request_id}' not found")
        if req["status"] != "approved":
            raise ValueError("Can only record execution for approved requests")

        req["execution_recorded"] = True
        entry = {
            "request_id": request_id,
            "capability_name": req["capability_name"],
            "action": req["action"],
            "outcome": outcome,
            "detail": detail,
            "executed_at": _now_iso(),
        }
        self._data["execution_log"].append(entry)
        if len(self._data["execution_log"]) > 500:
            self._data["execution_log"] = self._data["execution_log"][-500:]
        self._save()

    def pending_requests(self) -> List[Dict[str, Any]]:
        return [r for r in self._data["requests"] if r["status"] == "pending"]

    def get_request(self, request_id: str) -> Optional[Dict[str, Any]]:
        return self._find_request(request_id)

    def execution_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        return list(self._data["execution_log"][-limit:])

    def snapshot(self) -> Dict[str, Any]:
        counts = {status: 0 for status in AUTHORIZATION_STATUSES}
        for request in self._data["requests"]:
            status = request.get("status", "denied")
            counts[status] = counts.get(status, 0) + 1
        return {
            "total_requests": len(self._data["requests"]),
            "by_status": counts,
            "pending_count": counts.get("pending", 0),
            "execution_log_entries": len(self._data["execution_log"]),
            "pending_policy": "sovereign_gates_only",
        }
