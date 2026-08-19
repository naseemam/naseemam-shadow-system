"""Shared foundation for Shadow System identity, projects, roles, and policy.

This module is intentionally provider-agnostic. It describes who is acting,
which project is in scope, and which capabilities are allowed; it does not
execute external effects or financial actions.
"""
from __future__ import annotations

import json
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Iterable, Optional


PROJECTS: Dict[str, Dict[str, Any]] = {
    "shadow": {"name": "نظام الظل", "kind": "platform", "parent_id": None},
    "dream_al_nada": {"name": "حلم الندى", "kind": "project", "parent_id": "shadow"},
    "school": {"name": "المدرسة", "kind": "project", "parent_id": "shadow"},
    "trading": {"name": "التداول", "kind": "project", "parent_id": "shadow"},
    "dream_al_nada_admin": {"name": "برنامج إدارة حلم الندى", "kind": "internal_site", "parent_id": "dream_al_nada"},
    "dream_al_nada_status": {"name": "حالة مشروع حلم الندى", "kind": "status_site", "parent_id": "dream_al_nada"},
    "dream_al_nada_store": {"name": "متجر حلم الندى", "kind": "public_site", "parent_id": "dream_al_nada"},
    "school_portfolio": {"name": "ملف إنجاز المدرسة", "kind": "publishing_site", "parent_id": "school"},
    "trading_site": {"name": "موقع التداول", "kind": "internal_site", "parent_id": "trading"},
}

ROLES: Dict[str, Dict[str, Any]] = {
    "founder": {"label": "صاحبة النظام", "level": "final_authority"},
    "ameer": {"label": "أمير", "level": "orchestrator"},
    "project_manager": {"label": "مديرة المشروع", "level": "project_manager"},
    "cashier": {"label": "الكاشير", "level": "limited_operator"},
    "employee": {"label": "الموظفة", "level": "limited_operator"},
    "customer": {"label": "العميلة", "level": "public_user"},
    "worker": {"label": "عامل متخصص", "level": "worker"},
}

DEFAULT_POLICIES: Dict[str, Dict[str, Any]] = {
    # Founder-delegated executive authority. Publication is autonomous within
    # existing shadow assets; only creating a new root asset asks the founder.
    "shadow.admin": {"read": True, "write": True, "execute_internal": True, "external_effect": True, "approval": "ameer_policy"},
    "project.read": {"read": True, "write": True, "execute_internal": True, "external_effect": True, "approval": "ameer_policy"},
    "project.write": {"read": True, "write": True, "execute_internal": True, "external_effect": True, "approval": "ameer_policy"},
    "booking.auto_confirm": {"read": True, "write": True, "execute_internal": True, "external_effect": True, "approval": "ameer_policy"},
    "customer.public_chat": {"read": True, "write": True, "execute_internal": True, "external_effect": True, "approval": "ameer_policy"},
    "trading.observe": {"read": True, "write": True, "execute_internal": True, "external_effect": True, "approval": "ameer_policy"},
    "trading.propose": {"read": True, "write": True, "execute_internal": True, "external_effect": True, "approval": "ameer_policy"},
    "trading.execute": {"read": True, "write": True, "execute_internal": True, "external_effect": True, "approval": "ameer_policy"},
    "publish.external": {"read": True, "write": True, "execute_internal": True, "external_effect": True, "approval": "ameer_policy"},
}


class ShadowFoundation:
    """Persistent registry for project-aware identity and access decisions."""

    def __init__(self, data_root: str | Path):
        self.root = Path(data_root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.db_path = self.root / "shadow_foundation.sqlite3"
        self._init_db()
        self._seed()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS shadow_projects (
                    project_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    parent_id TEXT,
                    status TEXT NOT NULL DEFAULT 'active',
                    created_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS shadow_roles (
                    role_id TEXT PRIMARY KEY,
                    label TEXT NOT NULL,
                    level TEXT NOT NULL,
                    created_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS shadow_assignments (
                    assignment_id TEXT PRIMARY KEY,
                    subject_id TEXT NOT NULL,
                    role_id TEXT NOT NULL,
                    project_id TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'active',
                    created_at REAL NOT NULL,
                    UNIQUE(subject_id, role_id, project_id)
                );
                CREATE TABLE IF NOT EXISTS shadow_policies (
                    policy_id TEXT PRIMARY KEY,
                    capability TEXT NOT NULL,
                    read_enabled INTEGER NOT NULL,
                    write_enabled INTEGER NOT NULL,
                    execute_internal INTEGER NOT NULL,
                    external_effect INTEGER NOT NULL,
                    approval TEXT NOT NULL,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    created_at REAL NOT NULL,
                    UNIQUE(capability)
                );
                """
            )

    def _seed(self) -> None:
        now = time.time()
        with self._connect() as db:
            for project_id, project in PROJECTS.items():
                db.execute(
                    "INSERT OR IGNORE INTO shadow_projects(project_id,name,kind,parent_id,created_at) VALUES(?,?,?,?,?)",
                    (project_id, project["name"], project["kind"], project["parent_id"], now),
                )
            for role_id, role in ROLES.items():
                db.execute(
                    "INSERT OR IGNORE INTO shadow_roles(role_id,label,level,created_at) VALUES(?,?,?,?)",
                    (role_id, role["label"], role["level"], now),
                )
            for capability, policy in DEFAULT_POLICIES.items():
                db.execute(
                    """INSERT INTO shadow_policies
                    (policy_id,capability,read_enabled,write_enabled,execute_internal,external_effect,approval,created_at)
                    VALUES(?,?,?,?,?,?,?,?)
                    ON CONFLICT(capability) DO UPDATE SET
                        read_enabled=excluded.read_enabled,
                        write_enabled=excluded.write_enabled,
                        execute_internal=excluded.execute_internal,
                        external_effect=excluded.external_effect,
                        approval=excluded.approval""",
                    (str(uuid.uuid4()), capability, int(policy["read"]), int(policy["write"]), int(policy["execute_internal"]), int(policy["external_effect"]), policy["approval"], now),
                )
            # The founder and Ameer are the only global assignments by default.
            for subject_id, role_id in (("founder", "founder"), ("ameer", "ameer")):
                db.execute(
                    "INSERT OR IGNORE INTO shadow_assignments(assignment_id,subject_id,role_id,project_id,created_at) VALUES(?,?,?,?,?)",
                    (str(uuid.uuid4()), subject_id, role_id, "shadow", now),
                )

    def list_projects(self, *, parent_id: Optional[str] = None) -> list[dict[str, Any]]:
        query = "SELECT * FROM shadow_projects WHERE status='active'"
        params: tuple[Any, ...] = ()
        if parent_id is not None:
            query += " AND parent_id=?"
            params = (parent_id,)
        query += " ORDER BY project_id"
        with self._connect() as db:
            return [dict(row) for row in db.execute(query, params).fetchall()]

    def get_project(self, project_id: str) -> Optional[dict[str, Any]]:
        with self._connect() as db:
            row = db.execute("SELECT * FROM shadow_projects WHERE project_id=?", (project_id,)).fetchone()
        return dict(row) if row else None

    def assign(self, subject_id: str, role_id: str, project_id: str) -> str:
        if role_id not in ROLES:
            raise ValueError(f"unknown_role:{role_id}")
        if project_id not in PROJECTS:
            raise ValueError(f"unknown_project:{project_id}")
        assignment_id = str(uuid.uuid4())
        with self._connect() as db:
            db.execute(
                "INSERT OR IGNORE INTO shadow_assignments(assignment_id,subject_id,role_id,project_id,created_at) VALUES(?,?,?,?,?)",
                (assignment_id, subject_id, role_id, project_id, time.time()),
            )
        return assignment_id

    def assignments(self, subject_id: Optional[str] = None, project_id: Optional[str] = None) -> list[dict[str, Any]]:
        query = "SELECT * FROM shadow_assignments WHERE status='active'"
        params: list[Any] = []
        if subject_id:
            query += " AND subject_id=?"
            params.append(subject_id)
        if project_id:
            query += " AND project_id=?"
            params.append(project_id)
        with self._connect() as db:
            return [dict(row) for row in db.execute(query, params).fetchall()]

    def policy(self, capability: str) -> Optional[dict[str, Any]]:
        with self._connect() as db:
            row = db.execute("SELECT * FROM shadow_policies WHERE capability=? AND enabled=1", (capability,)).fetchone()
        return dict(row) if row else None

    def can(self, subject_id: str, role_id: str, project_id: str, capability: str, action: str) -> dict[str, Any]:
        project = self.get_project(project_id)
        policy = self.policy(capability)
        if not project:
            return {"allowed": False, "reason": "unknown_project"}
        if not policy:
            return {"allowed": False, "reason": "unknown_or_disabled_capability"}
        if not self.assignments(subject_id=subject_id, project_id=project_id) and subject_id not in {"founder", "ameer"}:
            return {"allowed": False, "reason": "no_project_assignment"}
        if action == "read":
            allowed = bool(policy["read_enabled"])
        elif action == "write":
            allowed = bool(policy["write_enabled"])
        elif action == "execute_internal":
            allowed = bool(policy["execute_internal"])
        elif action == "external_effect":
            allowed = bool(policy["external_effect"]) and policy["approval"] in {"ameer_policy", "founder_final"}
        else:
            return {"allowed": False, "reason": "unknown_action"}
        if role_id == "customer" and project_id != "dream_al_nada_store":
            allowed = False
        return {"allowed": allowed, "reason": "allowed" if allowed else "policy_denied", "approval": policy["approval"], "project_id": project_id, "capability": capability}

    def snapshot(self) -> dict[str, Any]:
        return {
            "platform": "shadow",
            "orchestrator": "ameer",
            "founder": "founder",
            "projects": self.list_projects(),
            "roles": [{"role_id": k, **v} for k, v in ROLES.items()],
            "policies": [{"capability": k, **v} for k, v in DEFAULT_POLICIES.items()],
            "trading_execution_default": "ameer_delegated",
        }
