from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class OperatorActivityStore:
    """Small persistent evidence ledger for the Founder-facing console.

    It stores execution metadata only, not chat contents, credentials, or approval
    identifiers. This makes the console useful across reloads without turning the
    public status surface into a transcript leak.
    """

    def __init__(self, workspace_root: str | Path) -> None:
        root = Path(workspace_root).resolve()
        data_root = Path(os.getenv("AMEER_DATA_DIR") or (root / ".ameer"))
        data_root.mkdir(parents=True, exist_ok=True)
        self.path = data_root / "operator_activity.json"
        self.data: Dict[str, Any] = {"events": []}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            parsed = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(parsed, dict) and isinstance(parsed.get("events"), list):
                self.data = parsed
        except (OSError, ValueError, json.JSONDecodeError):
            self.data = {"events": []}

    def _save(self) -> None:
        self.path.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")

    def record(self, evidence: Dict[str, Any], *, status: str = "completed") -> Dict[str, Any] | None:
        if not evidence.get("verified"):
            return None
        event = {
            "at": _now(),
            "status": status,
            "kind": str(evidence.get("kind") or "execution"),
            "completed_units": int(evidence.get("completed_units") or evidence.get("final_completed") or 0),
            "file_count": int(evidence.get("file_count") or 0),
            "files": [str(x) for x in (evidence.get("files") or [])[:20]],
            "stages": [str(x) for x in (evidence.get("stages") or [])[-12:]],
        }
        self.data.setdefault("events", []).append(event)
        self.data["events"] = self.data["events"][-200:]
        self._save()
        return event

    def recent(self, limit: int = 20) -> list[Dict[str, Any]]:
        safe_limit = max(1, min(int(limit), 100))
        return list(reversed(self.data.get("events", [])[-safe_limit:]))
