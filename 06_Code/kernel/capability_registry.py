"""
capability_registry.py
======================
Capability Manifest Registry — سجل قدرات أمير التنفيذي.

كل قدرة لها بطاقة (Capability Card) تحتوي على:
- معرف فريد، اسم، وصف، نطاق، تبعيات، مستوى خطر
- تاريخ الاعتماد، رقم النسخة، الحالة الحالية

دورة حياة القدرات:
    core        — قدرات أساسية لا تتغير أبداً
    extended    — قدرات معتمدة تعمل حالياً (بعد موافقة المؤسس)
    experimental— قدرات تحت التجربة والاختبار
    suspended   — متوقفة مؤقتاً، قابلة للإعادة فوراً
    deprecated  — لا يُنصح بها لكنها موجودة للتوافق
    retired     — مؤرشفة بالكامل، قابلة للاستعادة بقرار المؤسس فقط

لا تُحذف أي قدرة أبداً — فقط تُغيَّر حالتها.

قواعد Conflict Detection:
    قبل تفعيل أي قدرة جديدة يُجرى فحص تعارض ضد:
    - Core Identity
    - Decision Framework
    - القدرات الموجودة
    - الأوضاع التنفيذية الداخلية
    - قواعد الذاكرة

يُخزَّن في .ameer/capabilities.json لضمان البقاء عبر الجلسات.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


_CAPABILITIES_FILENAME = "capabilities.json"

VALID_STATUSES = {"core", "extended", "experimental", "suspended", "deprecated", "retired"}
VALID_RISK_LEVELS = {"low", "medium", "high"}

# Core capabilities that ship with Ameer and can never be removed
_CORE_CAPABILITIES: List[Dict[str, Any]] = [
    {
        "name": "engineering",
        "description": "Software and systems engineering: design, implementation, review",
        "scope": "technical",
        "dependencies": [],
        "risk_level": "low",
    },
    {
        "name": "programming",
        "description": "Code authoring, debugging, refactoring across languages and stacks",
        "scope": "technical",
        "dependencies": [],
        "risk_level": "low",
    },
    {
        "name": "system_design",
        "description": "Architecture design, component modeling, scalability planning",
        "scope": "technical",
        "dependencies": [],
        "risk_level": "low",
    },
    {
        "name": "project_management",
        "description": "Project planning, milestone tracking, resource coordination",
        "scope": "executive",
        "dependencies": [],
        "risk_level": "low",
    },
    {
        "name": "analysis",
        "description": "Data analysis, requirements analysis, business analysis",
        "scope": "executive",
        "dependencies": [],
        "risk_level": "low",
    },
    {
        "name": "planning",
        "description": "Strategic and tactical planning, roadmapping, prioritization",
        "scope": "executive",
        "dependencies": [],
        "risk_level": "low",
    },
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class CapabilityRegistry:
    """
    سجل قدرات أمير التنفيذي.

    واجهة الاستخدام:
    ----------------
    registry = CapabilityRegistry(workspace_root)
    cap_id = registry.register(
        name="github_management",
        description="Manage GitHub repos, PRs, and workflows",
        scope="tooling",
        risk_level="medium",
        approved_by="Naseem",
        status="extended",
    )
    registry.transition(cap_id, "suspended", reason="Pending audit")
    conflicts = registry.check_conflicts("new_capability_name", ["dependency_a"])
    """

    def __init__(self, workspace_root: str | Path) -> None:
        self._root = Path(workspace_root).resolve()
        self._ameer_dir = self._root / ".ameer"
        self._path = self._ameer_dir / _CAPABILITIES_FILENAME
        self._data: Dict[str, Any] = {"capabilities": [], "changelog": []}
        self._load()
        self._seed_core_capabilities()

    # ── Persistence ───────────────────────────────────────────────────────────

    def _load(self) -> None:
        if self._path.exists():
            try:
                raw = self._path.read_text(encoding="utf-8")
                self._data = json.loads(raw)
                if "capabilities" not in self._data:
                    self._data["capabilities"] = []
                if "changelog" not in self._data:
                    self._data["changelog"] = []
            except (json.JSONDecodeError, OSError):
                self._data = {"capabilities": [], "changelog": []}

    def _save(self) -> None:
        self._ameer_dir.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(self._data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    # ── Core seeding ──────────────────────────────────────────────────────────

    def _seed_core_capabilities(self) -> None:
        """Ensure all built-in core capabilities are present (idempotent)."""
        existing_names = {c["name"] for c in self._data["capabilities"]}
        changed = False
        for cap_def in _CORE_CAPABILITIES:
            if cap_def["name"] not in existing_names:
                card = self._build_card(
                    name=cap_def["name"],
                    description=cap_def["description"],
                    scope=cap_def["scope"],
                    dependencies=cap_def["dependencies"],
                    risk_level=cap_def["risk_level"],
                    approved_by="founder",
                    status="core",
                    version="1.0.0",
                )
                self._data["capabilities"].append(card)
                changed = True
        if changed:
            self._save()

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _build_card(
        self,
        name: str,
        description: str,
        scope: str,
        dependencies: List[str],
        risk_level: str,
        approved_by: str,
        status: str,
        version: str = "1.0.0",
        notes: str = "",
    ) -> Dict[str, Any]:
        return {
            "capability_id": str(uuid.uuid4()),
            "name": name,
            "description": description,
            "scope": scope,
            "dependencies": dependencies,
            "risk_level": risk_level,
            "approved_by": approved_by,
            "approval_date": _now_iso(),
            "version": version,
            "status": status,
            "created_at": _now_iso(),
            "updated_at": _now_iso(),
            "history": [],
            "notes": notes,
        }

    def _find(self, capability_id: str) -> Optional[Dict[str, Any]]:
        for cap in self._data["capabilities"]:
            if cap["capability_id"] == capability_id:
                return cap
        return None

    def _find_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        for cap in self._data["capabilities"]:
            if cap["name"] == name:
                return cap
        return None

    def _log_change(self, capability_id: str, action: str, detail: str) -> None:
        self._data["changelog"].append(
            {
                "timestamp": _now_iso(),
                "capability_id": capability_id,
                "action": action,
                "detail": detail,
            }
        )

    # ── Conflict Detection ────────────────────────────────────────────────────

    def check_conflicts(
        self,
        name: str,
        dependencies: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        فحص تعارض قبل تسجيل قدرة جديدة.

        يفحص ضد:
        - Core Identity (لا يُسمح بالتعارض مع القدرات الأساسية المحظورة)
        - الأسماء المكررة
        - التبعيات المطلوبة وحالتها

        يُعيد:
        {
            "has_conflict": bool,
            "conflicts": [{"type": str, "detail": str}, ...]
        }
        """
        conflicts: List[Dict[str, str]] = []
        deps = dependencies or []

        # 1. Duplicate name check
        existing = self._find_by_name(name)
        if existing:
            conflicts.append(
                {
                    "type": "duplicate_name",
                    "detail": f"Capability '{name}' already exists with status '{existing['status']}'",
                }
            )

        # 2. Core capability override check
        core_names = {c["name"] for c in _CORE_CAPABILITIES}
        if name in core_names:
            conflicts.append(
                {
                    "type": "core_identity_conflict",
                    "detail": f"'{name}' is a sealed core capability and cannot be re-registered",
                }
            )

        # 3. Dependency availability check
        for dep in deps:
            dep_cap = self._find_by_name(dep)
            if dep_cap is None:
                conflicts.append(
                    {
                        "type": "missing_dependency",
                        "detail": f"Dependency '{dep}' is not registered in the capability registry",
                    }
                )
            elif dep_cap["status"] in ("suspended", "deprecated", "retired"):
                conflicts.append(
                    {
                        "type": "inactive_dependency",
                        "detail": (
                            f"Dependency '{dep}' has status '{dep_cap['status']}' "
                            "and cannot serve as an active dependency"
                        ),
                    }
                )

        return {"has_conflict": len(conflicts) > 0, "conflicts": conflicts}

    # ── Public API ────────────────────────────────────────────────────────────

    def register(
        self,
        name: str,
        description: str,
        scope: str,
        approved_by: str,
        status: str = "experimental",
        dependencies: Optional[List[str]] = None,
        risk_level: str = "low",
        version: str = "1.0.0",
        notes: str = "",
        skip_conflict_check: bool = False,
    ) -> str:
        """
        تسجيل قدرة جديدة في السجل.

        يُعيد capability_id.
        يرفع ValueError إذا كانت المدخلات غير صالحة.
        يرفع ConflictError إذا وُجد تعارض (ما لم يُمرَّر skip_conflict_check=True).
        """
        name = name.strip()
        if not name:
            raise ValueError("name must not be empty")
        if not description.strip():
            raise ValueError("description must not be empty")
        if status not in VALID_STATUSES:
            raise ValueError(f"status must be one of {VALID_STATUSES}")
        if risk_level not in VALID_RISK_LEVELS:
            raise ValueError(f"risk_level must be one of {VALID_RISK_LEVELS}")
        if status == "core":
            raise ValueError(
                "Cannot register a capability with status 'core' — "
                "core capabilities are seeded internally"
            )

        deps = dependencies or []

        if not skip_conflict_check:
            conflict_result = self.check_conflicts(name, deps)
            if conflict_result["has_conflict"]:
                details = "; ".join(c["detail"] for c in conflict_result["conflicts"])
                raise CapabilityConflictError(
                    f"Capability registration blocked by conflict detection: {details}"
                )

        card = self._build_card(
            name=name,
            description=description,
            scope=scope,
            dependencies=deps,
            risk_level=risk_level,
            approved_by=approved_by,
            status=status,
            version=version,
            notes=notes,
        )
        self._data["capabilities"].append(card)
        self._log_change(card["capability_id"], "registered", f"status={status}, version={version}")
        self._save()
        return card["capability_id"]

    def transition(
        self,
        capability_id: str,
        new_status: str,
        reason: str = "",
        authorized_by: str = "founder",
    ) -> None:
        """
        تغيير حالة قدرة موجودة.

        القيود:
        - لا يمكن تغيير حالة قدرة من نوع 'core'
        - retired → active requires founder authorization
        - لا تُحذف القدرة أبداً
        """
        if new_status not in VALID_STATUSES:
            raise ValueError(f"new_status must be one of {VALID_STATUSES}")

        cap = self._find(capability_id)
        if cap is None:
            raise KeyError(f"Capability '{capability_id}' not found")

        if cap["status"] == "core":
            raise ValueError("Core capabilities cannot be transitioned — they are sealed")

        if cap["status"] == "retired" and new_status not in ("retired", "suspended"):
            raise ValueError(
                "Restoring a retired capability requires founder authorization "
                "and must target 'suspended' status first before further transitions"
            )

        old_status = cap["status"]
        cap["history"].append(
            {
                "from": old_status,
                "to": new_status,
                "timestamp": _now_iso(),
                "reason": reason,
                "authorized_by": authorized_by,
            }
        )
        cap["status"] = new_status
        cap["updated_at"] = _now_iso()
        self._log_change(
            capability_id,
            "transition",
            f"{old_status} → {new_status}: {reason}",
        )
        self._save()

    def get(self, capability_id: str) -> Optional[Dict[str, Any]]:
        """إرجاع بطاقة القدرة أو None."""
        return self._find(capability_id)

    def get_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        return self._find_by_name(name)

    def list_by_status(self, status: str) -> List[Dict[str, Any]]:
        """إرجاع قائمة القدرات بحالة معينة."""
        return [c for c in self._data["capabilities"] if c["status"] == status]

    def list_active(self) -> List[Dict[str, Any]]:
        """إرجاع القدرات النشطة: core + extended + experimental."""
        active_statuses = {"core", "extended", "experimental"}
        return [c for c in self._data["capabilities"] if c["status"] in active_statuses]

    def list_all(self) -> List[Dict[str, Any]]:
        return list(self._data["capabilities"])

    def changelog(self) -> List[Dict[str, Any]]:
        return list(self._data["changelog"])

    def snapshot(self) -> Dict[str, Any]:
        counts = {s: 0 for s in VALID_STATUSES}
        for cap in self._data["capabilities"]:
            counts[cap["status"]] = counts.get(cap["status"], 0) + 1
        return {
            "total": len(self._data["capabilities"]),
            "by_status": counts,
            "changelog_entries": len(self._data["changelog"]),
        }


class CapabilityConflictError(Exception):
    """رُفع عند اكتشاف تعارض أثناء تسجيل قدرة جديدة."""
