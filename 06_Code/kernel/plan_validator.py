"""
plan_validator.py
=================
Plan Validator — البوابة الوحيدة قبل الـ Scheduler.

أي Batch من المهام يجب أن يمر عبر هذه البوابة قبل الجدولة.
لا يُسمح لأي مكون بتجاوزها.

خمسة فحوصات إلزامية:

1. Task Completeness
   كل Task يجب أن تحتوي على: action, executor, target.

2. Dependency Graph
   لا توجد خطوة تعتمد على خطوة غير موجودة في الـ Batch.
   ولا توجد حلقات (cycles) في الاعتماديات.

3. Executor Availability
   الـ executor المطلوب لكل Task مسجّل في السجل المعروف.

4. Permission Compatibility
   إذا احتاجت المهمة capability، يجب أن تكون موجودة وممنوحة.
   وإذا كانت تتطلب موافقة، يُعلَم بذلك في المخرج.

5. Sandbox Safety
   target كل Task يجب أن يقع داخل runtime_workspace.
   لا يُسمح بالكتابة خارج الحدود.

المخرج القياسي:

{
  "valid": true,
  "warnings": [],
  "blocked": [],
  "summary": {
    "tasks": 7,
    "executors": ["file"],
    "approval_required": false
  }
}

أو عند الفشل:

{
  "valid": false,
  "blocked": [
    "Task task-001: missing required field 'action'",
    "Unknown executor: browser",
    "Target outside runtime_workspace: /etc/passwd"
  ],
  "warnings": [],
  "summary": { ... }
}
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


# ── Registered executor names ─────────────────────────────────────────────────
# هذه هي المنفّذات المعروفة في النظام.
# عند إضافة منفّذ جديد (P1.5 وما بعده) يُضاف هنا.
KNOWN_EXECUTORS: Set[str] = {
    "file",     # P1.5 File Executor — يكتب/يقرأ داخل runtime_workspace
    "shell",    # تنفيذ أوامر shell محدودة
    "memory",   # كتابة/قراءة الذاكرة
    "api",      # استدعاء API داخلي
}

# المسار الافتراضي لمنطقة التنفيذ الآمنة
_RUNTIME_WORKSPACE_DEFAULT = "09_Assets/runtime_workspace"


class PlanValidator:
    """
    البوابة الوحيدة التي تتحقق من صحة خطة التنفيذ قبل الجدولة.

    الاستخدام:
    ----------
    validator = PlanValidator(
        workspace_root="/path/to/workspace",
        capability_registry=kernel.capabilities,   # اختياري
        permission_registry=kernel.permissions,    # اختياري
    )

    result = validator.validate(tasks)
    if not result["valid"]:
        raise RuntimeError(result["blocked"])
    """

    def __init__(
        self,
        workspace_root: str | Path,
        capability_registry=None,
        permission_registry=None,
        runtime_workspace: Optional[str] = None,
    ) -> None:
        self._root = Path(workspace_root).resolve()
        self._capabilities = capability_registry
        self._permissions = permission_registry
        # المسار الآمن المسموح للكتابة فيه
        self._runtime_ws = self._root / (runtime_workspace or _RUNTIME_WORKSPACE_DEFAULT)

    # ── Public API ─────────────────────────────────────────────────────────────

    def validate(self, tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        تحقق من صحة قائمة المهام (Task Batch).

        يُعيد ValidationResult:
        {
            "valid":    bool,
            "blocked":  List[str],   # أسباب الرفض القاطع
            "warnings": List[str],   # تحذيرات غير قاطعة
            "summary":  {
                "tasks":            int,
                "executors":        List[str],
                "approval_required": bool,
            },
        }
        """
        blocked: List[str] = []
        warnings: List[str] = []
        executors_seen: Set[str] = set()
        approval_required = False

        task_ids: Set[str] = {t.get("id", "") for t in tasks if t.get("id")}

        for task in tasks:
            task_id = task.get("id") or task.get("title") or "<unnamed>"

            # ── Check 1: Task Completeness ─────────────────────────────────
            for required_field in ("action", "executor", "target"):
                if not task.get(required_field):
                    blocked.append(
                        f"Task '{task_id}': missing required field '{required_field}'"
                    )

            executor = task.get("executor", "")
            if executor:
                executors_seen.add(executor)

            # ── Check 2: Dependency Graph ──────────────────────────────────
            for dep_id in task.get("depends_on", []):
                if dep_id not in task_ids:
                    blocked.append(
                        f"Task '{task_id}': depends on unknown task '{dep_id}'"
                    )

            # ── Check 3: Executor Availability ────────────────────────────
            if executor and executor not in KNOWN_EXECUTORS:
                blocked.append(f"Task '{task_id}': unknown executor '{executor}'")

            # ── Check 4: Permission Compatibility ─────────────────────────
            capability_name = task.get("capability")
            if capability_name:
                cap_ok, perm_ok, needs_approval = self._check_permissions(
                    capability_name, task_id
                )
                if not cap_ok:
                    blocked.append(
                        f"Task '{task_id}': capability '{capability_name}' not found or inactive"
                    )
                elif not perm_ok:
                    if needs_approval:
                        approval_required = True
                        warnings.append(
                            f"Task '{task_id}': capability '{capability_name}' requires approval"
                        )
                    else:
                        blocked.append(
                            f"Task '{task_id}': capability '{capability_name}' not permitted"
                        )

            # ── Check 5: Sandbox Safety ────────────────────────────────────
            target = task.get("target", "")
            if target:
                sandbox_violation = self._check_sandbox(target)
                if sandbox_violation:
                    blocked.append(
                        f"Task '{task_id}': target outside runtime_workspace — {target}"
                    )

        # ── Dependency Cycle Detection ─────────────────────────────────────────
        cycle = self._detect_cycle(tasks)
        if cycle:
            blocked.append(f"Dependency cycle detected: {' → '.join(cycle)}")

        valid = len(blocked) == 0

        return {
            "valid": valid,
            "blocked": blocked,
            "warnings": warnings,
            "summary": {
                "tasks": len(tasks),
                "executors": sorted(executors_seen),
                "approval_required": approval_required,
            },
        }

    # ── Internal helpers ───────────────────────────────────────────────────────

    def _check_permissions(
        self, capability_name: str, task_id: str
    ) -> "tuple[bool, bool, bool]":
        """
        يُعيد (capability_ok, permission_ok, needs_approval).

        إذا لم تكن سجلات القدرات/الصلاحيات متوفرة (وضع standalone)،
        نفترض أن كل شيء مسموح حتى تتوفر الربط الكامل.
        """
        if self._capabilities is None:
            return True, True, False

        cap = self._capabilities.get_by_name(capability_name)
        if cap is None:
            return False, False, False

        active_statuses = {"core", "extended", "experimental"}
        if cap.get("status") not in active_statuses:
            return False, False, False

        if self._permissions is None:
            return True, True, False

        cap_id = cap.get("id", "")
        perm_card = self._permissions.get_for_capability(cap_id)
        if perm_card is None:
            # صلاحية غير معرّفة بعد — تُعامَل كـ requires_approval
            return True, False, True

        status = perm_card.get("permission_status", "not_granted")
        if status == "granted" and perm_card.get("enabled", False):
            return True, True, False
        elif status == "requires_approval":
            return True, False, True
        else:
            return True, False, False

    def _check_sandbox(self, target: str) -> bool:
        """
        يُعيد True إذا كان الـ target يخرج عن منطقة runtime_workspace.

        يتجاهل الأهداف غير المسارية مثل URIs أو معرّفات قواعد البيانات.
        """
        # تجاهل URIs مثل memory:// أو https:// أو db://
        if "://" in target:
            return False

        # إذا لم يبدأ الهدف بحرف مسار مألوف، فهو ليس مسار ملف
        if not re.match(r'^[./~a-zA-Z0-9]', target):
            return False

        try:
            # حوّل إلى مسار مطلق بالنسبة للجذر
            if os.path.isabs(target):
                resolved = Path(target).resolve()
            else:
                resolved = (self._root / target).resolve()

            # يجب أن يكون المسار داخل runtime_workspace تمامًا
            runtime_ws_resolved = self._runtime_ws.resolve()
            return not resolved.is_relative_to(runtime_ws_resolved)
        except Exception:
            # مسار غير صالح — نعتبره انتهاك
            return True

    def _detect_cycle(self, tasks: List[Dict[str, Any]]) -> List[str]:
        """
        يُعيد قائمة بمسار الحلقة إذا وُجدت، أو قائمة فارغة.
        يستخدم DFS مع تتبع المسار الحالي.
        """
        graph: Dict[str, List[str]] = {}
        for task in tasks:
            tid = task.get("id", "")
            if tid:
                graph[tid] = [d for d in task.get("depends_on", []) if d]

        visited: Set[str] = set()
        path: List[str] = []

        def dfs(node: str) -> Optional[List[str]]:
            if node in path:
                cycle_start = path.index(node)
                return path[cycle_start:] + [node]
            if node in visited:
                return None
            visited.add(node)
            path.append(node)
            for neighbour in graph.get(node, []):
                result = dfs(neighbour)
                if result:
                    return result
            path.pop()
            return None

        for node in list(graph.keys()):
            if node not in visited:
                result = dfs(node)
                if result:
                    return result

        return []
