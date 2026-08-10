"""
execution_authorization.py
===========================
Execution Authorization — تفويض تنفيذ الإجراءات.

هذه الطبقة هي الحارس الأخير قبل أي تنفيذ عملي.
حتى لو كانت القدرة موجودة والصلاحية ممنوحة،
يجب أن يحصل كل إجراء على تفويض تنفيذ صريح.

حالات التفويض:
    approved  — مُفوَّض للتنفيذ
    denied    — مرفوض صراحةً
    pending   — ينتظر موافقة المؤسس

Pipeline التفويض الكامل:
    check_capability()   ← هل يملك أمير القدرة؟
    check_permission()   ← هل الصلاحية ممنوحة؟
    authorize()          ← تفويض التنفيذ الآني (pending → approved/denied)
    record_execution()   ← تسجيل كل تنفيذ حقيقي

يُخزَّن في .ameer/execution_auth.json لضمان البقاء عبر الجلسات.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from kernel.capability_registry import CapabilityRegistry
from kernel.permission_registry import PermissionRegistry


_EXEC_AUTH_FILENAME = "execution_auth.json"

AUTHORIZATION_STATUSES = {"approved", "denied", "pending"}
_FILE_READ_SCOPE_KIND = "runtime_workspace_only"
_FILE_READ_SCOPE_ROOT = "09_Assets/runtime_workspace"
_FILE_READ_TOOL_NAME = "file.read"
_FILE_READ_ACTION = "read"


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def file_read_permission_scope() -> str:
    return json.dumps(
        {
            "tool_name": _FILE_READ_TOOL_NAME,
            "action": _FILE_READ_ACTION,
            "scope_kind": _FILE_READ_SCOPE_KIND,
            "scope_root": _FILE_READ_SCOPE_ROOT,
        },
        ensure_ascii=False,
        sort_keys=True,
    )


class ExecutionAuthorization:
    """
    تفويض التنفيذ الآني — الطبقة الأخيرة في سلسلة الحوكمة.

    واجهة الاستخدام:
    ----------------
    auth = ExecutionAuthorization(workspace_root, capability_registry, permission_registry)

    # فحص ما إذا كان الإجراء مسموحاً به
    result = auth.check(
        capability_name="github_management",
        action="merge_pull_request",
        context={"repo": "my-repo", "pr": 42},
    )
    # result.status ∈ {"approved", "denied", "pending"}

    # تفويض صريح من المؤسس
    auth.authorize(request_id, authorized_by="Naseem")

    # تسجيل تنفيذ حقيقي
    auth.record_execution(request_id, outcome="success", detail="PR #42 merged")
    """

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
        self._load()

    # ── Persistence ───────────────────────────────────────────────────────────

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

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _find_request(self, request_id: str) -> Optional[Dict[str, Any]]:
        for r in self._data["requests"]:
            if r["request_id"] == request_id:
                return r
        return None

    @staticmethod
    def _parse_scope_policy(scope: Any) -> Dict[str, Any]:
        if not isinstance(scope, str) or not scope.strip():
            return {}
        try:
            parsed = json.loads(scope)
        except (TypeError, ValueError, json.JSONDecodeError):
            return {}
        return parsed if isinstance(parsed, dict) else {}

    def _file_operation_scope_denial_reason(
        self,
        *,
        action: str,
        context: Optional[Dict[str, Any]],
        perm_card: Dict[str, Any],
    ) -> str:
        policy = self._parse_scope_policy(perm_card.get("scope"))
        required_policy = self._parse_scope_policy(file_read_permission_scope())
        if policy != required_policy:
            return "Permission scope does not authorize registry-owned file.read"

        if str(action or "").strip().lower() != _FILE_READ_ACTION:
            return "Permission scope is limited to file.read/read only"

        safe_context = context or {}
        tool_name = str(safe_context.get("tool_name") or "").strip().lower()
        if tool_name != _FILE_READ_TOOL_NAME:
            return "Permission scope requires registry-owned tool file.read"

        target = safe_context.get("target")
        if not isinstance(target, str) or not target.strip():
            return "Permission scope requires an in-scope file.read target"

        normalized_target = target.strip().replace("\\", "/")
        allowed_prefix = f"{_FILE_READ_SCOPE_ROOT}/"
        if normalized_target != _FILE_READ_SCOPE_ROOT and not normalized_target.startswith(allowed_prefix):
            return "Permission scope requires target inside 09_Assets/runtime_workspace"

        return ""

    # ── Public API ────────────────────────────────────────────────────────────

    def check(
        self,
        capability_name: str,
        action: str,
        context: Optional[Dict[str, Any]] = None,
        requested_by: str = "executive_brain",
    ) -> Dict[str, Any]:
        """
        فحص ما إذا كان الإجراء مسموحاً به وإنشاء طلب تفويض.

        يُعيد:
        {
            "request_id": str,
            "status": "approved" | "denied" | "pending",
            "capability_name": str,
            "action": str,
            "reason": str,
        }

        القواعد:
        1. إذا لم تكن القدرة موجودة أو نشطة → denied
        2. إذا لم تكن الصلاحية ممنوحة → denied
        3. إذا كانت permission_status=requires_approval → pending
        4. إذا كانت الصلاحية ممنوحة كاملاً → approved
        """
        request_id = str(uuid.uuid4())
        now = _now_iso()

        # Step 1: capability check
        cap = self._caps.get_by_name(capability_name)
        if cap is None:
            result = self._make_result(
                request_id, "denied", capability_name, action,
                f"Capability '{capability_name}' is not registered",
                context, requested_by, now,
            )
            self._persist_request(result)
            return result

        active_statuses = {"core", "extended", "experimental"}
        if cap["status"] not in active_statuses:
            result = self._make_result(
                request_id, "denied", capability_name, action,
                f"Capability '{capability_name}' has status '{cap['status']}' and is not active",
                context, requested_by, now,
            )
            self._persist_request(result)
            return result

        # Step 2: permission check
        perm_card = self._perms.get_for_capability(cap["capability_id"])
        if perm_card is None or not perm_card.get("owned", False):
            result = self._make_result(
                request_id, "denied", capability_name, action,
                "No permission card found for this capability",
                context, requested_by, now,
            )
            self._persist_request(result)
            return result

        if not perm_card.get("enabled", False):
            result = self._make_result(
                request_id, "denied", capability_name, action,
                "Capability is disabled in Permission Registry",
                context, requested_by, now,
            )
            self._persist_request(result)
            return result

        if perm_card.get("is_expired", False):
            result = self._make_result(
                request_id, "denied", capability_name, action,
                "Permission has expired",
                context, requested_by, now,
            )
            self._persist_request(result)
            return result

        perm_status = perm_card.get("permission_status", "not_granted")

        if perm_status == "not_granted":
            result = self._make_result(
                request_id, "denied", capability_name, action,
                "Permission not granted for this capability",
                context, requested_by, now,
            )
            self._persist_request(result)
            return result

        if perm_status == "requires_approval":
            result = self._make_result(
                request_id, "pending", capability_name, action,
                "Requires explicit Founder approval for this execution",
                context, requested_by, now,
            )
            self._persist_request(result)
            return result

        if capability_name == "file_operations":
            scope_denial_reason = self._file_operation_scope_denial_reason(
                action=action,
                context=context,
                perm_card=perm_card,
            )
            if scope_denial_reason:
                result = self._make_result(
                    request_id,
                    "denied",
                    capability_name,
                    action,
                    scope_denial_reason,
                    context,
                    requested_by,
                    now,
                )
                self._persist_request(result)
                return result

        # permission_status == "granted"
        result = self._make_result(
            request_id, "approved", capability_name, action,
            "Capability owned, enabled, and permission granted",
            context, requested_by, now,
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
        # Keep last 200 requests
        if len(self._data["requests"]) > 200:
            self._data["requests"] = self._data["requests"][-200:]
        self._save()

    def authorize(
        self,
        request_id: str,
        authorized_by: str = "founder",
    ) -> None:
        """
        موافقة المؤسس على تنفيذ طلب pending.
        يُحوِّل الحالة من pending إلى approved.
        """
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
        """رفض طلب تنفيذ pending."""
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
        """
        تسجيل تنفيذ حقيقي بعد approved.
        outcome ∈ {"success", "failure", "partial"}
        """
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
        counts = {s: 0 for s in AUTHORIZATION_STATUSES}
        for r in self._data["requests"]:
            s = r.get("status", "denied")
            counts[s] = counts.get(s, 0) + 1
        return {
            "total_requests": len(self._data["requests"]),
            "by_status": counts,
            "pending_count": counts.get("pending", 0),
            "execution_log_entries": len(self._data["execution_log"]),
        }
