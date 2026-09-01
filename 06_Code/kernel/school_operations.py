from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


SCHOOL_TASK_CATEGORIES = {
    "student_follow_up": "متابعة الطالبات",
    "school_records": "السجلات والقوائم",
    "achievement_portfolio": "ملف الإنجاز",
    "general": "مهام المدرسة",
}
SCHOOL_TASK_PRIORITIES = {"high", "normal", "low"}


class SchoolOperations:
    """Local school-record domain managed by Ameer.

    This is intentionally independent from any external school portal. External
    synchronization must be added through an official API or approved credential.
    """

    def __init__(self, workspace_root: str | Path) -> None:
        root = Path(workspace_root).resolve()
        data_root = Path(__import__("os").getenv("AMEER_DATA_DIR") or (root / ".ameer"))
        data_root.mkdir(parents=True, exist_ok=True)
        self.db_path = data_root / "school_records.sqlite3"
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.db_path)
        con.row_factory = sqlite3.Row
        return con

    def _init_db(self) -> None:
        with self._conn() as con:
            con.executescript(
                """
                CREATE TABLE IF NOT EXISTS students (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    student_ref TEXT DEFAULT '',
                    grade TEXT DEFAULT '',
                    section TEXT DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'active',
                    notes TEXT DEFAULT ''
                );
                CREATE TABLE IF NOT EXISTS school_tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id INTEGER,
                    title TEXT NOT NULL,
                    due_at TEXT DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'open',
                    priority TEXT DEFAULT 'normal',
                    category TEXT NOT NULL DEFAULT 'general',
                    missing_inputs TEXT DEFAULT '',
                    notes TEXT DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT '',
                    completed_at TEXT DEFAULT '',
                    FOREIGN KEY(student_id) REFERENCES students(id)
                );
                CREATE TABLE IF NOT EXISTS grades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id INTEGER NOT NULL,
                    subject TEXT NOT NULL,
                    score REAL,
                    max_score REAL,
                    term TEXT DEFAULT '',
                    notes TEXT DEFAULT '',
                    FOREIGN KEY(student_id) REFERENCES students(id)
                );
                CREATE TABLE IF NOT EXISTS attendance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id INTEGER NOT NULL,
                    day TEXT NOT NULL,
                    status TEXT NOT NULL,
                    notes TEXT DEFAULT '',
                    UNIQUE(student_id, day),
                    FOREIGN KEY(student_id) REFERENCES students(id)
                );
                """
            )
            columns = {row[1] for row in con.execute("PRAGMA table_info(school_tasks)")}
            migrations = {
                "category": "ALTER TABLE school_tasks ADD COLUMN category TEXT NOT NULL DEFAULT 'general'",
                "missing_inputs": "ALTER TABLE school_tasks ADD COLUMN missing_inputs TEXT DEFAULT ''",
                "created_at": "ALTER TABLE school_tasks ADD COLUMN created_at TEXT NOT NULL DEFAULT ''",
                "completed_at": "ALTER TABLE school_tasks ADD COLUMN completed_at TEXT DEFAULT ''",
            }
            for column, statement in migrations.items():
                if column not in columns:
                    con.execute(statement)

    def add_student(self, name: str, *, student_ref: str = "", grade: str = "", section: str = "", notes: str = "") -> Dict[str, Any]:
        with self._conn() as con:
            cur = con.execute(
                "INSERT INTO students(name, student_ref, grade, section, notes) VALUES(?,?,?,?,?)",
                (name, student_ref, grade, section, notes),
            )
            student_id = cur.lastrowid
        return {"id": student_id, "name": name, "student_ref": student_ref, "grade": grade, "section": section}

    def update_student(self, student_id: int, changes: Dict[str, Any]) -> Dict[str, Any]:
        allowed = {"name", "student_ref", "grade", "section", "status", "notes"}
        clean = {k: v for k, v in (changes or {}).items() if k in allowed}
        if not clean:
            return {"status": "no_changes", "student_id": student_id}
        fields = ", ".join(f"{k}=?" for k in clean)
        with self._conn() as con:
            con.execute(f"UPDATE students SET {fields} WHERE id=?", [*clean.values(), student_id])
        return {"status": "updated", "student_id": student_id, "changes": clean}

    def list_students(self, status: Optional[str] = "active") -> List[Dict[str, Any]]:
        with self._conn() as con:
            if status:
                rows = con.execute("SELECT * FROM students WHERE status=? ORDER BY name", (status,)).fetchall()
            else:
                rows = con.execute("SELECT * FROM students ORDER BY name").fetchall()
        return [dict(r) for r in rows]

    def add_task(
        self,
        title: str,
        *,
        student_id: Optional[int] = None,
        due_at: str = "",
        priority: str = "normal",
        category: str = "general",
        missing_inputs: str = "",
        notes: str = "",
    ) -> Dict[str, Any]:
        title = str(title or "").strip()
        if not title:
            raise ValueError("task_title_required")
        priority = priority if priority in SCHOOL_TASK_PRIORITIES else "normal"
        category = category if category in SCHOOL_TASK_CATEGORIES else "general"
        created_at = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
        with self._conn() as con:
            cur = con.execute(
                "INSERT INTO school_tasks(student_id,title,due_at,priority,category,missing_inputs,notes,created_at) VALUES(?,?,?,?,?,?,?,?)",
                (student_id, title, due_at, priority, category, missing_inputs, notes, created_at),
            )
            task_id = cur.lastrowid
        return {
            "id": task_id,
            "title": title,
            "student_id": student_id,
            "due_at": due_at,
            "priority": priority,
            "category": category,
            "missing_inputs": missing_inputs,
        }

    def update_task(self, task_id: int, changes: Dict[str, Any]) -> Dict[str, Any]:
        allowed = {"title", "student_id", "due_at", "status", "priority", "category", "missing_inputs", "notes"}
        clean = {key: value for key, value in (changes or {}).items() if key in allowed}
        if "priority" in clean and clean["priority"] not in SCHOOL_TASK_PRIORITIES:
            clean["priority"] = "normal"
        if "category" in clean and clean["category"] not in SCHOOL_TASK_CATEGORIES:
            clean["category"] = "general"
        if clean.get("status") == "done":
            clean["completed_at"] = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
        elif "status" in clean:
            clean["completed_at"] = ""
        if not clean:
            return {"status": "no_changes", "task_id": task_id}
        fields = ", ".join(f"{key}=?" for key in clean)
        with self._conn() as con:
            exists = con.execute("SELECT 1 FROM school_tasks WHERE id=?", (task_id,)).fetchone()
            if not exists:
                raise KeyError("school_task_not_found")
            con.execute(f"UPDATE school_tasks SET {fields} WHERE id=?", [*clean.values(), task_id])
        return {"status": "updated", "task_id": task_id, "changes": clean}

    def list_tasks(self, status: Optional[str] = "open") -> List[Dict[str, Any]]:
        with self._conn() as con:
            if status:
                rows = con.execute("SELECT * FROM school_tasks WHERE status=? ORDER BY due_at, id", (status,)).fetchall()
            else:
                rows = con.execute("SELECT * FROM school_tasks ORDER BY due_at, id").fetchall()
        return [dict(r) for r in rows]

    @staticmethod
    def _due_date(value: str) -> Optional[date]:
        raw = str(value or "").strip()
        if not raw:
            return None
        try:
            return date.fromisoformat(raw[:10])
        except ValueError:
            return None

    def weekly_plan(self, *, today: Optional[date] = None) -> Dict[str, Any]:
        """Build a concise, deterministic weekly plan from persisted school work."""
        current_day = today or date.today()
        tasks = self.list_tasks(status="open")

        def enrich(task: Dict[str, Any]) -> Dict[str, Any]:
            item = dict(task)
            due = self._due_date(item.get("due_at", ""))
            days_until = (due - current_day).days if due else None
            flags: List[str] = []
            if days_until is not None and days_until < 0:
                flags.append(f"متأخر {abs(days_until)} يوم")
            elif days_until == 0:
                flags.append("موعده اليوم")
            elif days_until is not None and days_until <= 7:
                flags.append(f"موعده خلال {days_until} يوم")
            if str(item.get("missing_inputs") or "").strip():
                flags.append("مدخلات ناقصة")
            item["category_label"] = SCHOOL_TASK_CATEGORIES.get(item.get("category"), SCHOOL_TASK_CATEGORIES["general"])
            item["days_until_due"] = days_until
            item["attention_flags"] = flags
            return item

        enriched = [enrich(task) for task in tasks]
        priority_rank = {"high": 0, "normal": 1, "low": 2}

        def rank(item: Dict[str, Any]) -> tuple:
            days = item.get("days_until_due")
            deadline_rank = 0 if days is not None and days < 0 else 1 if days is not None and days <= 7 else 2
            due_rank = days if days is not None else 10_000
            return (deadline_rank, priority_rank.get(item.get("priority"), 1), due_rank, item.get("id", 0))

        ordered = sorted(enriched, key=rank)
        by_category = {
            key: [item for item in ordered if item.get("category") == key]
            for key in SCHOOL_TASK_CATEGORIES
        }
        deadlines = [item for item in ordered if item.get("days_until_due") is not None and item["days_until_due"] <= 7]
        missing = [item for item in ordered if str(item.get("missing_inputs") or "").strip()]
        return {
            "generated_for": current_day.isoformat(),
            "prioritized": ordered,
            "categories": by_category,
            "deadlines": deadlines,
            "missing_inputs": missing,
            "next_three": ordered[:3],
        }

    def record_grade(self, student_id: int, subject: str, *, score: float, max_score: float = 100, term: str = "", notes: str = "") -> Dict[str, Any]:
        with self._conn() as con:
            cur = con.execute(
                "INSERT INTO grades(student_id,subject,score,max_score,term,notes) VALUES(?,?,?,?,?,?)",
                (student_id, subject, score, max_score, term, notes),
            )
        return {"id": cur.lastrowid, "student_id": student_id, "subject": subject, "score": score, "max_score": max_score, "term": term}

    def record_attendance(self, student_id: int, day: str, status: str, *, notes: str = "") -> Dict[str, Any]:
        with self._conn() as con:
            con.execute(
                "INSERT INTO attendance(student_id,day,status,notes) VALUES(?,?,?,?) ON CONFLICT(student_id,day) DO UPDATE SET status=excluded.status, notes=excluded.notes",
                (student_id, day, status, notes),
            )
        return {"student_id": student_id, "day": day, "status": status}

    def dashboard(self) -> Dict[str, Any]:
        with self._conn() as con:
            students = con.execute("SELECT COUNT(*) FROM students WHERE status='active'").fetchone()[0]
            open_tasks = con.execute("SELECT COUNT(*) FROM school_tasks WHERE status='open'").fetchone()[0]
            grade_count = con.execute("SELECT COUNT(*) FROM grades").fetchone()[0]
            completed_tasks = con.execute("SELECT COUNT(*) FROM school_tasks WHERE status='done'").fetchone()[0]
            rows = con.execute(
                "SELECT category, COUNT(*) AS count FROM school_tasks WHERE status='open' GROUP BY category"
            ).fetchall()
        breakdown = {key: 0 for key in SCHOOL_TASK_CATEGORIES}
        breakdown.update({row["category"]: row["count"] for row in rows})
        return {
            "students": students,
            "open_tasks": open_tasks,
            "completed_tasks": completed_tasks,
            "grade_records": grade_count,
            "task_breakdown": breakdown,
            "weekly_plan": self.weekly_plan(),
        }
