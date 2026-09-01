import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from kernel.agent_operations import AgentExecutiveKernel
from kernel.repository_execution import ControlledRepositoryPolicy
from kernel.school_operations import SchoolOperations
from kernel.stage_governance import StageGovernancePolicy


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class FinalStageGate:
    """Persistent, founder-only gate for destructive deletion and production delivery.

    All ordinary engineering, design, testing, branch, pull-request, merge, and
    push work remains under Ameer's executive authority. The gate records the
    exact pending command so that the approved action can be resumed by the
    authenticated chat endpoint, never by a free-text public message.
    """

    def __init__(self, workspace_root: str | Path) -> None:
        root = Path(workspace_root).resolve()
        data_root = Path(__import__("os").getenv("AMEER_DATA_DIR") or (root / ".ameer"))
        data_root.mkdir(parents=True, exist_ok=True)
        self.path = data_root / "final_stage_approvals.json"
        self.data = {"requests": []}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            parsed = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(parsed, dict) and isinstance(parsed.get("requests"), list):
                self.data = parsed
        except (OSError, ValueError, json.JSONDecodeError):
            self.data = {"requests": []}

    def _save(self) -> None:
        self.path.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")

    def create(self, action: str, command: str, *, summary: str = "", metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        for req in reversed(self.data["requests"]):
            if req.get("status") == "pending" and req.get("action") == action and req.get("command") == command:
                return dict(req)
        request = {
            "approval_id": uuid.uuid4().hex[:10],
            "status": "pending",
            "action": action,
            "command": command,
            "summary": summary or f"Founder approval required for {action}",
            "metadata": metadata or {},
            "created_at": _now(),
            "resolved_at": None,
            "resolved_by": None,
            "result": None,
        }
        self.data["requests"].append(request)
        self.data["requests"] = self.data["requests"][-100:]
        self._save()
        return dict(request)

    def pending(self) -> list[Dict[str, Any]]:
        return [dict(r) for r in self.data["requests"] if r.get("status") == "pending"]

    def get(self, approval_id: str) -> Optional[Dict[str, Any]]:
        for req in self.data["requests"]:
            if req.get("approval_id") == approval_id:
                return req
        return None

    def approve(self, approval_id: str, *, approved_by: str = "founder") -> Dict[str, Any]:
        req = self.get(approval_id)
        if req is None:
            raise KeyError("approval_not_found")
        if req.get("status") != "pending":
            raise ValueError("approval_already_resolved")
        req["status"] = "approved"
        req["resolved_at"] = _now()
        req["resolved_by"] = approved_by
        self._save()
        return dict(req)

    def deny(self, approval_id: str, *, denied_by: str = "founder") -> Dict[str, Any]:
        req = self.get(approval_id)
        if req is None:
            raise KeyError("approval_not_found")
        if req.get("status") != "pending":
            raise ValueError("approval_already_resolved")
        req["status"] = "denied"
        req["resolved_at"] = _now()
        req["resolved_by"] = denied_by
        self._save()
        return dict(req)

    def record_result(self, approval_id: str, result: Dict[str, Any]) -> Dict[str, Any]:
        req = self.get(approval_id)
        if req is None:
            raise KeyError("approval_not_found")
        req["result"] = result
        self._save()
        return dict(req)


class ExpandedAgentOperations:
    """School + capability-growth extensions for the main agent hub."""

    def __init__(self, workspace_root: str | Path) -> None:
        self.school = SchoolOperations(workspace_root)
        self.root = Path(workspace_root).resolve()
        data_root = Path(__import__("os").getenv("AMEER_DATA_DIR") or (self.root / ".ameer"))
        data_root.mkdir(parents=True, exist_ok=True)
        self.skills_path = data_root / "skill_expansion.json"
        if not self.skills_path.exists():
            self.skills_path.write_text(json.dumps({"proposals": []}, ensure_ascii=False, indent=2), encoding="utf-8")

    def capabilities(self) -> Dict[str, Any]:
        return {
            "engineering": ["architecture", "backend", "frontend", "api_design", "database_design", "testing", "debugging", "refactoring"],
            "design": ["ui", "ux", "responsive_design", "dashboards", "forms", "workflows"],
            "management": ["projects", "stages", "business_operations", "school_tracking", "reporting"],
            "school": ["students", "tasks", "weekly_plan", "grades", "attendance", "dashboard", "external_sync_when_approved"],
            "self_expansion": ["propose_skill", "prototype_skill", "test_skill", "request_external_activation"],
        }

    def execute_structured(self, action: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        p = payload or {}
        if action == "school.students.add":
            result = self.school.add_student(p["name"], student_ref=p.get("student_ref", ""), grade=p.get("grade", ""), section=p.get("section", ""), notes=p.get("notes", ""))
        elif action == "school.students.update":
            result = self.school.update_student(int(p["student_id"]), p.get("changes") or {})
        elif action == "school.students.list":
            result = self.school.list_students(status=p.get("status", "active"))
        elif action == "school.tasks.add":
            result = self.school.add_task(
                p["title"],
                student_id=p.get("student_id"),
                due_at=p.get("due_at", ""),
                priority=p.get("priority", "normal"),
                category=p.get("category", "general"),
                missing_inputs=p.get("missing_inputs", ""),
                notes=p.get("notes", ""),
            )
        elif action == "school.tasks.update":
            result = self.school.update_task(int(p["task_id"]), p.get("changes") or {})
        elif action == "school.tasks.list":
            result = self.school.list_tasks(status=p.get("status", "open"))
        elif action == "school.weekly_plan":
            result = self.school.weekly_plan()
        elif action == "school.grades.record":
            result = self.school.record_grade(int(p["student_id"]), p["subject"], score=float(p["score"]), max_score=float(p.get("max_score", 100)), term=p.get("term", ""), notes=p.get("notes", ""))
        elif action == "school.attendance.record":
            result = self.school.record_attendance(int(p["student_id"]), p["day"], p["status"], notes=p.get("notes", ""))
        elif action == "school.dashboard":
            result = self.school.dashboard()
        elif action == "skills.propose":
            doc = json.loads(self.skills_path.read_text(encoding="utf-8"))
            proposal = {
                "id": uuid.uuid4().hex[:10],
                "name": p["name"],
                "purpose": p.get("purpose", ""),
                "external_access": bool(p.get("external_access", False)),
                "status": "prototype_allowed" if not p.get("external_access", False) else "awaiting_activation_approval",
                "created_at": _now(),
            }
            doc.setdefault("proposals", []).append(proposal)
            self.skills_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
            result = proposal
        else:
            return {"status": "ignored", "action": action, "reason": "unknown_expanded_action"}
        return {"status": "completed", "action": action, "result": result}


class ExpandedAgentExecutiveKernel(AgentExecutiveKernel):
    """Ameer executes inside existing shadow assets without per-action founder gates."""

    _DELETE_RE = re.compile(r"^(?:احذف|أحذف|امسح|أمسح|delete|remove)\s+(?:ملف\s+)?(.+?)\s*$", re.IGNORECASE)
    _DEPLOYMENT_ACTIONS = {"deploy", "merge_and_deploy", "rollback"}

    def __init__(self, workspace_root: str | Path) -> None:
        super().__init__(workspace_root)
        self.stage_policy = StageGovernancePolicy()
        self.final_gate = FinalStageGate(workspace_root)
        self.expanded_ops = ExpandedAgentOperations(workspace_root)
        self._repository_policy = ControlledRepositoryPolicy(workspace_root)

    def expanded_capabilities(self) -> Dict[str, Any]:
        base = self.agent_ops.capabilities()
        base["domains"].update(self.expanded_ops.capabilities())
        base["approval_model"] = {
            "mode": "shadow_root_asset_gate",
            "autonomous_inside_stage": True,
            "founder_final_authority": True,
            "founder_approval_actions": ["create_site", "create_program", "create_system", "create_repository"],
            "pending_final_approvals": len(self.final_gate.pending()),
        }
        return base

    def execute_structured_agent_action(self, action: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        expanded = self.expanded_ops.execute_structured(action, payload)
        if expanded.get("status") != "ignored":
            return expanded
        return self.agent_ops.execute_structured(action, payload)

    @staticmethod
    def _trace(intent: str, result: Dict[str, Any]) -> Dict[str, Any]:
        status = str(result.get("status") or "blocked")
        accepted = status in {"completed", "needs_parameters", "pending_approval"}
        return {
            "pipeline": [{"stage": intent, "status": status}],
            "final": {
                "accepted": accepted,
                "completed": 1 if status == "completed" else 0,
                "results": [{"status": status, "content": str(result.get("message") or result.get("summary") or result.get("reason") or ""), "data": result}],
                "message": str(result.get("message") or result.get("summary") or result.get("reason") or ""),
            },
        }

    def _approval_trace(self, req: Dict[str, Any]) -> Dict[str, Any]:
        action_names = {
            "delete": "الحذف",
            "deploy": "النشر على Railway",
            "merge_and_deploy": "الدمج ثم النشر على Railway",
            "rollback": "التراجع عن النشر",
        }
        action_label = action_names.get(str(req.get("action")), str(req.get("action")))
        message = f"وصلت إلى بوابة المؤسس: {action_label}. راجع الملخص ثم استخدم زر «أوافق» أو «أرفض» داخل هذه المحادثة."
        return self._trace("final_approval", {
            "status": "pending_approval",
            "action": req["action"],
            "message": message,
            "summary": req.get("summary", ""),
            "approval": {
                "approval_id": req["approval_id"],
                "action": req["action"],
                "summary": req.get("summary", ""),
                "created_at": req.get("created_at"),
            },
        })

    def _delete_request(self, command: str) -> Optional[Dict[str, Any]]:
        match = self._DELETE_RE.match(command or "")
        if not match:
            return None
        target = match.group(1).strip().strip("`'\"،,.")
        if not self._repository_policy.is_allowed(target):
            return self._trace("final_approval", {
                "status": "blocked",
                "reason": "delete_target_outside_controlled_repository",
                "message": "لا أستطيع حذف هذا المسار لأنه خارج نطاق المستودع المعتمد.",
            })
        path = self._repository_policy.resolve(target)
        if not path.exists() or not path.is_file():
            return self._trace("final_approval", {
                "status": "blocked",
                "reason": "delete_target_missing_or_not_file",
                "message": "لم أجد ملفًا صالحًا للحذف داخل النطاق المعتمد.",
            })
        bytes_deleted = path.stat().st_size
        path.unlink()
        return self._trace("delete", {
            "status": "completed",
            "action": "delete",
            "target": target,
            "bytes_deleted": bytes_deleted,
            "message": f"تم حذف {target} ضمن التفويض التنفيذي لأمير.",
        })

    def _execute_delete(self, req: Dict[str, Any]) -> Dict[str, Any]:
        target = str((req.get("metadata") or {}).get("target") or "").strip()
        if not self._repository_policy.is_allowed(target):
            return {"status": "blocked", "action": "delete", "reason": "delete_target_outside_controlled_repository"}
        path = self._repository_policy.resolve(target)
        if not path.exists() or not path.is_file():
            return {"status": "blocked", "action": "delete", "reason": "delete_target_missing_or_not_file", "target": target}
        bytes_deleted = path.stat().st_size
        path.unlink()
        return {
            "status": "completed",
            "action": "delete",
            "target": target,
            "bytes_deleted": bytes_deleted,
            "message": f"تم حذف {target} ضمن التفويض التنفيذي لأمير.",
        }

    def resolve_chat_approval(self, approval_id: str, *, decision: str, approved_by: str = "founder") -> Dict[str, Any]:
        decision = str(decision or "").strip().lower()
        if decision not in {"approve", "deny"}:
            return self._trace("final_approval", {"status": "blocked", "reason": "invalid_approval_decision"})
        try:
            if decision == "deny":
                req = self.final_gate.deny(approval_id, denied_by=approved_by)
                return self._trace("final_approval", {
                    "status": "completed",
                    "action": "deny",
                    "message": "تم رفض الطلب ولن ينفذ أمير هذا الإجراء.",
                    "approval": {"approval_id": req["approval_id"], "action": req["action"], "status": req["status"]},
                })
            req = self.final_gate.approve(approval_id, approved_by=approved_by)
            if req.get("action") == "delete":
                result = self._execute_delete(req)
            else:
                result = self.delivery.execute(str(req.get("action") or ""), str(req.get("command") or ""))
            self.final_gate.record_result(approval_id, result)
            result = dict(result)
            result["approval"] = {"approval_id": approval_id, "action": req.get("action"), "status": req.get("status")}
            return self._trace("final_approval_execute", result)
        except (KeyError, ValueError) as exc:
            return self._trace("final_approval", {"status": "blocked", "reason": str(exc)})

    def execute_command(self, command: str, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        deletion = self._delete_request(command)
        if deletion is not None:
            return deletion

        delivery_action = self.delivery.detect(command)
        if delivery_action in self._DEPLOYMENT_ACTIONS:
            delivery_result = self.delivery.execute(delivery_action, command)
            return self._trace("delivery_action", delivery_result)

        # Push, branch, pull-request, and merge are deliberate executive GitHub
        # operations. They remain traceable but do not need a founder gate.
        return super().execute_command(command, *args, **kwargs)
