from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from kernel.agent_operations import AgentExecutiveKernel
from kernel.school_operations import SchoolOperations
from kernel.stage_governance import StageGovernancePolicy


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class FinalStageGate:
    """One meaningful Founder approval at the end of a stage.

    Internal, reversible work does not create approvals. Merge/deploy/irreversible
    activation is queued here and executed only after explicit Founder approval.
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

    def create(self, action: str, command: str, *, summary: str = "") -> Dict[str, Any]:
        # Reuse an identical pending gate rather than pestering the Founder repeatedly.
        for req in reversed(self.data["requests"]):
            if req.get("status") == "pending" and req.get("action") == action and req.get("command") == command:
                return req
        request = {
            "approval_id": uuid.uuid4().hex[:10],
            "status": "pending",
            "action": action,
            "command": command,
            "summary": summary or f"Final approval required for {action}",
            "created_at": _now(),
            "resolved_at": None,
        }
        self.data["requests"].append(request)
        self.data["requests"] = self.data["requests"][-100:]
        self._save()
        return request

    def pending(self) -> list[Dict[str, Any]]:
        return [r for r in self.data["requests"] if r.get("status") == "pending"]

    def get(self, approval_id: str) -> Optional[Dict[str, Any]]:
        for req in self.data["requests"]:
            if req.get("approval_id") == approval_id:
                return req
        return None

    def approve(self, approval_id: str) -> Dict[str, Any]:
        req = self.get(approval_id)
        if req is None:
            raise KeyError("approval_not_found")
        if req.get("status") != "pending":
            raise ValueError("approval_already_resolved")
        req["status"] = "approved"
        req["resolved_at"] = _now()
        self._save()
        return req

    def deny(self, approval_id: str) -> Dict[str, Any]:
        req = self.get(approval_id)
        if req is None:
            raise KeyError("approval_not_found")
        req["status"] = "denied"
        req["resolved_at"] = _now()
        self._save()
        return req


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
            "school": ["students", "tasks", "grades", "attendance", "dashboard", "external_sync_when_approved"],
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
            result = self.school.add_task(p["title"], student_id=p.get("student_id"), due_at=p.get("due_at", ""), priority=p.get("priority", "normal"), notes=p.get("notes", ""))
        elif action == "school.tasks.list":
            result = self.school.list_tasks(status=p.get("status", "open"))
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
    """Ameer as a founder-governed multi-domain operating agent."""

    APPROVAL_RE = re.compile(r"(?:وافق|أوافق|approve)\s+(?:على\s+)?([a-f0-9]{6,20})", re.IGNORECASE)
    DENY_RE = re.compile(r"(?:ارفض|أرفض|رفض|deny)\s+(?:على\s+)?([a-f0-9]{6,20})", re.IGNORECASE)

    def __init__(self, workspace_root: str | Path) -> None:
        super().__init__(workspace_root)
        self.stage_policy = StageGovernancePolicy()
        self.final_gate = FinalStageGate(workspace_root)
        self.expanded_ops = ExpandedAgentOperations(workspace_root)

    def expanded_capabilities(self) -> Dict[str, Any]:
        base = self.agent_ops.capabilities()
        base["domains"].update(self.expanded_ops.capabilities())
        base["approval_model"] = {
            "mode": "final_gate_only",
            "autonomous_inside_stage": True,
            "founder_final_authority": True,
            "pending_final_approvals": len(self.final_gate.pending()),
        }
        return base

    def execute_structured_agent_action(self, action: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        expanded = self.expanded_ops.execute_structured(action, payload)
        if expanded.get("status") != "ignored":
            return expanded
        return self.agent_ops.execute_structured(action, payload)

    def _approval_trace(self, req: Dict[str, Any]) -> Dict[str, Any]:
        message = (
            f"أنهيت العمل الداخلي ووصلت للبوابة النهائية. أحتاج موافقتك مرة واحدة لتنفيذ {req['action']}. "
            f"رقم الموافقة: {req['approval_id']}"
        )
        return self._trace("final_approval", {
            "status": "needs_parameters",
            "action": req["action"],
            "message": message,
            "approval": req,
        })

    def execute_command(self, command: str, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        approve = self.APPROVAL_RE.search(command or "")
        if approve:
            approval_id = approve.group(1)
            try:
                req = self.final_gate.approve(approval_id)
                result = self.delivery.execute(req["action"], req["command"])
                return self._trace("final_approval_execute", result)
            except (KeyError, ValueError) as exc:
                return self._trace("final_approval", {"status": "blocked", "reason": str(exc)})

        deny = self.DENY_RE.search(command or "")
        if deny:
            try:
                req = self.final_gate.deny(deny.group(1))
                return self._trace("final_approval", {"status": "completed", "action": "deny", "result": req})
            except (KeyError, ValueError) as exc:
                return self._trace("final_approval", {"status": "blocked", "reason": str(exc)})

        delivery_action = self.delivery.detect(command)
        if delivery_action in {"merge", "deploy", "merge_and_deploy", "rollback"}:
            req = self.final_gate.create(delivery_action, command, summary="Founder final gate for external delivery")
            return self._approval_trace(req)

        return super().execute_command(command, *args, **kwargs)
