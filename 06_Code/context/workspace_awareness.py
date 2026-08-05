"""
workspace_awareness.py
======================
Workspace Awareness — إدراك بيئة العمل تلقائيًا.

أمير لا يسأل المؤسسة عن معلومات يمكنه اكتشافها بنفسه.
يُشغَّل عند كل startup ويُنتج ملخصًا تنفيذيًا للوضع الراهن.
"""

from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional


def _run(cmd: List[str], cwd: str, timeout: int = 8) -> str:
    try:
        result = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True,
            check=False, timeout=timeout,
        )
        return (result.stdout or "").strip()
    except Exception:
        return ""


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class WorkspaceAwareness:
    """
    يفحص بيئة العمل تلقائيًا ويُنتج ملخصًا تنفيذيًا.

    يكتشف:
    - حالة git (branch، commits، ملفات تغيرت)
    - ملفات الذاكرة التي تغيرت
    - المهام المعلّقة
    - صحة النظام
    """

    def __init__(self, workspace_root: str | Path) -> None:
        self._root = str(Path(workspace_root).resolve())

    # ── Git Awareness ─────────────────────────────────────────────────────────

    def _get_branch(self) -> str:
        return _run(["git", "rev-parse", "--abbrev-ref", "HEAD"], self._root) or "unknown"

    def _get_recent_commits(self, n: int = 5) -> List[str]:
        raw = _run(
            ["git", "log", f"--max-count={n}", "--oneline", "--no-decorate"],
            self._root,
        )
        return [line.strip() for line in raw.splitlines() if line.strip()]

    def _get_changed_files(self, since: str = "HEAD~1") -> List[str]:
        raw = _run(["git", "diff", "--name-only", since, "HEAD"], self._root)
        if not raw:
            raw = _run(["git", "status", "--short"], self._root)
        lines = [line.strip() for line in raw.splitlines() if line.strip()]
        # Normalise "XY path" format from git status
        cleaned = []
        for line in lines:
            parts = line.split(None, 1)
            cleaned.append(parts[-1] if len(parts) == 2 else line)
        return cleaned[:10]

    def _get_current_tag(self) -> str:
        return _run(["git", "describe", "--tags", "--abbrev=0"], self._root) or ""

    def _get_commit_sha(self) -> str:
        return _run(["git", "rev-parse", "--short", "HEAD"], self._root) or "unknown"

    # ── Memory / Document Changes ─────────────────────────────────────────────

    def _get_recently_modified_docs(self, max_age_days: int = 7) -> List[str]:
        """ملفات .md التي تغيرت مؤخرًا."""
        modified: List[str] = []
        try:
            for dirpath, _, filenames in os.walk(self._root):
                # Skip backup / cache dirs
                rel_dir = os.path.relpath(dirpath, self._root).replace("\\", "/")
                if any(seg in rel_dir for seg in ["08_Backups", "__pycache__", ".git"]):
                    continue
                for fname in filenames:
                    if not fname.endswith(".md"):
                        continue
                    fpath = os.path.join(dirpath, fname)
                    try:
                        mtime = os.path.getmtime(fpath)
                        age_days = (datetime.now().timestamp() - mtime) / 86400
                        if age_days <= max_age_days:
                            modified.append(
                                os.path.relpath(fpath, self._root).replace("\\", "/")
                            )
                    except Exception:
                        continue
        except Exception:
            pass
        return modified[:8]

    # ── Pending Tasks ─────────────────────────────────────────────────────────

    def _get_pending_tasks(self) -> List[Dict]:
        tasks_path = Path(self._root) / ".ameer" / "tasks.json"
        if not tasks_path.exists():
            return []
        try:
            data = json.loads(tasks_path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return [t for t in data if t.get("status") not in {"done", "failed"}]
        except Exception:
            pass
        return []

    def _get_pending_approvals(self) -> List[Dict]:
        state_path = Path(self._root) / ".ameer" / "state.json"
        if not state_path.exists():
            return []
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
            return [a for a in state.get("pending_approvals", []) if a.get("status") == "pending"]
        except Exception:
            return []

    # ── Main Scan ─────────────────────────────────────────────────────────────

    def scan(self) -> Dict:
        """
        تشغيل الفحص الكامل وإعادة قاموس بالنتائج.
        """
        branch = self._get_branch()
        commits = self._get_recent_commits()
        changed = self._get_changed_files()
        tag = self._get_current_tag()
        sha = self._get_commit_sha()
        recent_docs = self._get_recently_modified_docs()
        pending_tasks = self._get_pending_tasks()
        pending_approvals = self._get_pending_approvals()

        return {
            "scanned_at": _now_iso(),
            "git": {
                "branch": branch,
                "commit": sha,
                "tag": tag,
                "recent_commits": commits,
                "changed_files": changed,
            },
            "documents": {
                "recently_modified": recent_docs,
            },
            "tasks": {
                "pending_count": len(pending_tasks),
                "pending": pending_tasks[:5],
            },
            "approvals": {
                "pending_count": len(pending_approvals),
                "pending": pending_approvals[:5],
            },
        }

    def build_executive_summary(self, scan_result: Optional[Dict] = None) -> str:
        """
        يُنتج ملخصًا تنفيذيًا قصيرًا للوضع الراهن.
        يُضاف إلى system prompt في أول رسالة بالجلسة.
        """
        data = scan_result or self.scan()
        parts: List[str] = []

        git = data.get("git", {})
        branch = git.get("branch", "")
        tag = git.get("tag", "")
        sha = git.get("commit", "")
        commits = git.get("recent_commits", [])
        changed = git.get("changed_files", [])

        parts.append(f"الفرع: {branch}" + (f" | الوسم: {tag}" if tag else "") + f" | Commit: {sha}")

        if commits:
            parts.append(f"آخر commit: {commits[0]}")

        if changed:
            parts.append(f"ملفات تغيّرت: {', '.join(changed[:4])}" + (" وأخرى" if len(changed) > 4 else ""))

        docs = data.get("documents", {}).get("recently_modified", [])
        if docs:
            parts.append(f"وثائق محدَّثة مؤخرًا: {', '.join(docs[:3])}")

        tasks = data.get("tasks", {})
        if tasks.get("pending_count", 0) > 0:
            parts.append(f"مهام معلّقة: {tasks['pending_count']}")

        approvals = data.get("approvals", {})
        if approvals.get("pending_count", 0) > 0:
            parts.append(f"قرارات تنتظر موافقتكِ: {approvals['pending_count']}")

        if not parts:
            return ""

        return "[ وضع المشروع الآن: " + " | ".join(parts) + " ]"
