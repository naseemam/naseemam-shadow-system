"""
senses_persistence.py
=====================
Persistent state, calibration metadata, and event feed for Ameer Extended Senses.
"""

from __future__ import annotations

import json
import threading
from collections import deque
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class PersistentJsonStore:
    def __init__(self, path: Path, default: Mapping[str, Any]) -> None:
        self.path = Path(path)
        self.default = dict(default)
        self._lock = threading.RLock()
        self._data: Dict[str, Any] = self._load()

    def _load(self) -> Dict[str, Any]:
        if not self.path.exists():
            return dict(self.default)
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else dict(self.default)
        except (OSError, json.JSONDecodeError):
            return dict(self.default)

    def save(self) -> None:
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(self.path.suffix + ".tmp")
            tmp.write_text(json.dumps(self._data, ensure_ascii=False, indent=2), encoding="utf-8")
            tmp.replace(self.path)


class PersistentSensesCatalog(PersistentJsonStore):
    """Persists presentation descriptors and latest normalized sensor frames."""

    def __init__(self, workspace_root: Path) -> None:
        super().__init__(
            Path(workspace_root) / ".ameer" / "senses_catalog.json",
            {"presentations": {}, "last_frames": {}, "updated_at": None},
        )

    def put_presentation(self, presentation: Mapping[str, Any]) -> None:
        pid = str(presentation.get("presentation_id") or "").strip()
        if not pid:
            raise ValueError("presentation_id required")
        with self._lock:
            self._data.setdefault("presentations", {})[pid] = dict(presentation)
            self._data["updated_at"] = _now_iso()
            self.save()

    def remove_presentation(self, presentation_id: str) -> None:
        with self._lock:
            self._data.setdefault("presentations", {}).pop(presentation_id, None)
            self._data["updated_at"] = _now_iso()
            self.save()

    def presentations(self) -> List[Dict[str, Any]]:
        return list(self._data.get("presentations", {}).values())

    def put_frame(self, sensor_id: str, frame: Mapping[str, Any]) -> None:
        with self._lock:
            self._data.setdefault("last_frames", {})[sensor_id] = dict(frame)
            self._data["updated_at"] = _now_iso()
            self.save()

    def last_frame(self, sensor_id: str) -> Optional[Dict[str, Any]]:
        item = self._data.get("last_frames", {}).get(sensor_id)
        return dict(item) if isinstance(item, dict) else None

    def snapshot(self) -> Dict[str, Any]:
        return {
            "presentation_count": len(self._data.get("presentations", {})),
            "last_frame_count": len(self._data.get("last_frames", {})),
            "updated_at": self._data.get("updated_at"),
            "path": str(self.path),
        }


class CalibrationRegistry(PersistentJsonStore):
    """Stores device calibration metadata without inventing calibration values."""

    def __init__(self, workspace_root: Path) -> None:
        super().__init__(
            Path(workspace_root) / ".ameer" / "senses_calibration.json",
            {"sensors": {}, "updated_at": None},
        )

    def set(self, sensor_id: str, calibration: Mapping[str, Any]) -> Dict[str, Any]:
        if not sensor_id.strip():
            raise ValueError("sensor_id required")
        record = {**dict(calibration), "sensor_id": sensor_id, "updated_at": _now_iso()}
        with self._lock:
            self._data.setdefault("sensors", {})[sensor_id] = record
            self._data["updated_at"] = record["updated_at"]
            self.save()
        return dict(record)

    def get(self, sensor_id: str) -> Optional[Dict[str, Any]]:
        value = self._data.get("sensors", {}).get(sensor_id)
        return dict(value) if isinstance(value, dict) else None

    def list(self) -> List[Dict[str, Any]]:
        return [dict(v) for v in self._data.get("sensors", {}).values() if isinstance(v, dict)]


@dataclass(frozen=True)
class SensesEvent:
    event_id: int
    event_type: str
    timestamp: str
    payload: Mapping[str, Any]


class SensesEventBus:
    """Small in-process replayable event feed for SSE/WebSocket transports."""

    def __init__(self, max_events: int = 500) -> None:
        self._events = deque(maxlen=max_events)
        self._next_id = 1
        self._lock = threading.RLock()

    def publish(self, event_type: str, payload: Mapping[str, Any]) -> Dict[str, Any]:
        with self._lock:
            event = SensesEvent(self._next_id, event_type, _now_iso(), dict(payload))
            self._next_id += 1
            self._events.append(event)
            return asdict(event)

    def since(self, event_id: int = 0) -> List[Dict[str, Any]]:
        with self._lock:
            return [asdict(event) for event in self._events if event.event_id > event_id]

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "buffered_events": len(self._events),
                "last_event_id": self._events[-1].event_id if self._events else 0,
            }
