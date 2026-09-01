from __future__ import annotations

import json
import os
import re
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


EXECUTION_ID_RE = re.compile(r"^[A-Za-z0-9_-]{16,64}$")


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class LiveExecutionStore:
    """Founder-facing lifecycle updates for business-chat requests.

    The store intentionally excludes prompts, model reasoning, credentials and
    raw tool payloads. It persists only short operational stages that are safe
    to render in the live execution card.
    """

    def __init__(self, workspace_root: str | Path) -> None:
        root = Path(workspace_root).resolve()
        data_root = Path(os.getenv("AMEER_DATA_DIR") or (root / ".ameer"))
        data_root.mkdir(parents=True, exist_ok=True)
        self.path = data_root / "live_executions.json"
        self._lock = threading.RLock()
        self.data: Dict[str, Any] = {"executions": {}}
        self._load()

    @staticmethod
    def valid_execution_id(execution_id: str) -> bool:
        return bool(EXECUTION_ID_RE.fullmatch(str(execution_id or "")))

    def _load(self) -> None:
        with self._lock:
            if not self.path.exists():
                self.data = {"executions": {}}
                return
            try:
                parsed = json.loads(self.path.read_text(encoding="utf-8"))
                executions = parsed.get("executions") if isinstance(parsed, dict) else None
                self.data = {"executions": executions if isinstance(executions, dict) else {}}
            except (OSError, ValueError, json.JSONDecodeError):
                self.data = {"executions": {}}

    def _save(self) -> None:
        self.path.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")

    def begin(self, execution_id: str, *, request_id: str = "") -> Dict[str, Any]:
        if not self.valid_execution_id(execution_id):
            raise ValueError("invalid_execution_id")
        with self._lock:
            self._load()
            now = _now()
            item = {
                "execution_id": execution_id,
                "request_id": str(request_id or "")[:64],
                "status": "running",
                "started_at": now,
                "updated_at": now,
                "stages": [],
            }
            self.data["executions"][execution_id] = item
            self._trim()
            self._save()
            return dict(item)

    def stage(
        self,
        execution_id: str,
        key: str,
        title: str,
        *,
        status: str = "completed",
        detail: str = "",
        evidence: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        if not self.valid_execution_id(execution_id):
            return None
        safe_status = status if status in {"pending", "running", "completed", "blocked", "failed"} else "running"
        with self._lock:
            self._load()
            item = self.data["executions"].get(execution_id)
            if not isinstance(item, dict):
                item = self.begin(execution_id)
            now = _now()
            stages = item.setdefault("stages", [])
            existing = next((stage for stage in stages if stage.get("key") == key), None)
            safe_evidence = self._safe_evidence(evidence or {})
            stage = {
                "key": str(key or "stage")[:48],
                "title": str(title or "مرحلة تنفيذ")[:160],
                "detail": str(detail or "")[:320],
                "status": safe_status,
                "updated_at": now,
                "evidence": safe_evidence,
            }
            if existing is None:
                stage["started_at"] = now
                stages.append(stage)
            else:
                stage["started_at"] = existing.get("started_at") or now
                existing.clear()
                existing.update(stage)
            item["updated_at"] = now
            if safe_status in {"failed", "blocked"}:
                item["status"] = safe_status
            self._save()
            return self.public(execution_id)

    def finish(self, execution_id: str, *, status: str = "completed") -> Optional[Dict[str, Any]]:
        if not self.valid_execution_id(execution_id):
            return None
        safe_status = status if status in {"completed", "blocked", "failed"} else "completed"
        with self._lock:
            self._load()
            item = self.data["executions"].get(execution_id)
            if not isinstance(item, dict):
                return None
            item["status"] = safe_status
            item["updated_at"] = _now()
            item["finished_at"] = item["updated_at"]
            self._save()
            return self.public(execution_id)

    def public(self, execution_id: str) -> Optional[Dict[str, Any]]:
        if not self.valid_execution_id(execution_id):
            return None
        with self._lock:
            self._load()
            item = self.data["executions"].get(execution_id)
            if not isinstance(item, dict):
                return None
            return {
                "execution_id": item.get("execution_id"),
                "status": item.get("status", "running"),
                "started_at": item.get("started_at"),
                "updated_at": item.get("updated_at"),
                "finished_at": item.get("finished_at"),
                "stages": [dict(stage) for stage in item.get("stages", [])[-20:]],
            }

    @staticmethod
    def _safe_evidence(evidence: Dict[str, Any]) -> Dict[str, Any]:
        allowed = {"worker_id", "run_id", "file_count", "completed_units", "test_count", "preview_url"}
        clean = {key: evidence[key] for key in allowed if key in evidence and evidence[key] is not None}
        if isinstance(evidence.get("files"), list):
            clean["files"] = [str(path)[:180] for path in evidence["files"][:8]]
        return clean

    def _trim(self) -> None:
        executions = self.data.get("executions", {})
        if len(executions) <= 100:
            return
        ordered = sorted(executions.items(), key=lambda pair: pair[1].get("updated_at", ""), reverse=True)
        self.data["executions"] = dict(ordered[:100])
