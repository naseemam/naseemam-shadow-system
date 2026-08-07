"""
executor_file.py
================
P1.5 File Executor — ينفّذ عمليات الملفات داخل runtime_workspace فقط.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict


_RUNTIME_WORKSPACE_DEFAULT = "09_Assets/runtime_workspace"


class FileExecutor:
    def __init__(self, workspace_root: str | Path, runtime_workspace: str = _RUNTIME_WORKSPACE_DEFAULT) -> None:
        self._root = Path(workspace_root).resolve()
        self._runtime_workspace = (self._root / runtime_workspace).resolve()

    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        action = str(task.get("action", "")).lower().strip()
        task_id = str(task.get("id") or "<unnamed>")
        target = str(task.get("target", "")).strip()

        try:
            path = self._resolve_target(target)
        except ValueError:
            return {
                "task_id": task_id,
                "status": "blocked",
                "reason": "target_outside_runtime_workspace",
                "target": target,
            }

        if action in {"write", "create"}:
            content = str(task.get("content", ""))
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            return {
                "task_id": task_id,
                "status": "completed",
                "action": action,
                "path": str(path),
                "relative_path": str(path.relative_to(self._root)).replace("\\", "/"),
                "bytes_written": len(content.encode("utf-8")),
            }

        if action == "append":
            content = str(task.get("content", ""))
            path.parent.mkdir(parents=True, exist_ok=True)
            prefix = ""
            if path.exists():
                with path.open("rb") as handle:
                    handle.seek(0, 2)
                    if handle.tell() > 0:
                        handle.seek(-1, 2)
                        if handle.read(1) != b"\n":
                            prefix = "\n"
            with path.open("a", encoding="utf-8") as handle:
                handle.write(prefix + content)
            return {
                "task_id": task_id,
                "status": "completed",
                "action": action,
                "path": str(path),
                "relative_path": str(path.relative_to(self._root)).replace("\\", "/"),
                "bytes_written": len((prefix + content).encode("utf-8")),
            }

        if action == "read":
            if not path.exists():
                return {
                    "task_id": task_id,
                    "status": "failed",
                    "reason": "file_missing",
                    "path": str(path),
                }
            content = path.read_text(encoding="utf-8")
            return {
                "task_id": task_id,
                "status": "completed",
                "action": action,
                "path": str(path),
                "relative_path": str(path.relative_to(self._root)).replace("\\", "/"),
                "content": content,
            }

        return {
            "task_id": task_id,
            "status": "failed",
            "reason": "unsupported_action",
            "action": action,
            "target": target,
        }

    def _resolve_target(self, target: str) -> Path:
        path = (self._root / target).resolve() if not Path(target).is_absolute() else Path(target).resolve()
        if not path.is_relative_to(self._runtime_workspace):
            raise ValueError("target_outside_runtime_workspace")
        return path
