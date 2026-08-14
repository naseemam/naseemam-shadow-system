from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional


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
                    notes TEXT DEFAULT '',
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

    def add_task(self, title: str, *, student_id: Optional[int] = None, due_at: str = "", priority: str = "normal", notes: str = "") -> Dict[str, Any]:
        with self._conn() as con:
            cur = con.execute(
                "INSERT INTO school_tasks(student_id,title,due_at,priority,notes) VALUES(?,?,?,?,?)",
                (student_id, title, due_at, priority, notes),
            )
            task_id = cur.lastrowid
        return {"id": task_id, "title": title, "student_id": student_id, "due_at": due_at, "priority": priority}

    def list_tasks(self, status: Optional[str] = "open") -> List[Dict[str, Any]]:
        with self._conn() as con:
            if status:
                rows = con.execute("SELECT * FROM school_tasks WHERE status=? ORDER BY due_at, id", (status,)).fetchall()
            else:
                rows = con.execute("SELECT * FROM school_tasks ORDER BY due_at, id").fetchall()
        return [dict(r) for r in rows]

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
        return {"students": students, "open_tasks": open_tasks, "grade_records": grade_count}
