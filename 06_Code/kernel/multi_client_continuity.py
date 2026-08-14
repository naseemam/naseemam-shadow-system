from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


SUPPORTED_CLIENTS = {"desktop_local", "desktop_web", "mobile_app", "web_app"}
SUPPORTED_CHANNELS = {"text", "voice"}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class MultiClientContinuity:
    """Persistent device/channel continuity for one Ameer agent identity.

    Clients are presentation surfaces only. They all resolve to the same backend
    agent kernel, memory, tasks, approvals, business data, and delivery state.
    """

    def __init__(self, workspace_root: str | Path) -> None:
        data_root = Path(os.getenv("AMEER_DATA_DIR") or workspace_root).resolve()
        self.root = data_root / ".ameer"
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "multi_client_sessions.json"
        self.api_token = (os.getenv("AMEER_AGENT_API_TOKEN") or "").strip()
        self._data: Dict[str, Any] = {"clients": {}, "sessions": {}, "active_session_id": None}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                self._data.update(raw)
        except (OSError, json.JSONDecodeError):
            pass

    def _save(self) -> None:
        self.path.write_text(json.dumps(self._data, ensure_ascii=False, indent=2), encoding="utf-8")

    @property
    def authentication_enabled(self) -> bool:
        return bool(self.api_token)

    def authorized(self, authorization_header: str, *, local_request: bool = False) -> bool:
        if local_request:
            return True
        if not self.api_token:
            return False
        value = (authorization_header or "").strip()
        if not value.lower().startswith("bearer "):
            return False
        supplied = value[7:].strip()
        return hmac.compare_digest(supplied, self.api_token)

    def register_client(
        self,
        *,
        client_id: str,
        client_type: str,
        channel: str,
        device_name: str = "",
        app_version: str = "",
    ) -> Dict[str, Any]:
        if client_type not in SUPPORTED_CLIENTS:
            raise ValueError(f"unsupported_client_type:{client_type}")
        if channel not in SUPPORTED_CHANNELS:
            raise ValueError(f"unsupported_channel:{channel}")
        cid = (client_id or "").strip() or secrets.token_urlsafe(12)
        existing = self._data["clients"].get(cid) or {}
        card = {
            "client_id": cid,
            "client_type": client_type,
            "channel": channel,
            "device_name": device_name,
            "app_version": app_version,
            "registered_at": existing.get("registered_at") or _now(),
            "last_seen_at": _now(),
        }
        self._data["clients"][cid] = card
        self._save()
        return card

    def open_session(self, *, client_id: str, channel: Optional[str] = None) -> Dict[str, Any]:
        client = self._data["clients"].get(client_id)
        if not client:
            raise KeyError("client_not_registered")
        use_channel = channel or client.get("channel") or "text"
        if use_channel not in SUPPORTED_CHANNELS:
            raise ValueError("unsupported_channel")

        active = self._data.get("active_session_id")
        if active and active in self._data["sessions"]:
            session = self._data["sessions"][active]
            session["client_id"] = client_id
            session["channel"] = use_channel
            session["last_seen_at"] = _now()
        else:
            sid = secrets.token_urlsafe(18)
            session = {
                "session_id": sid,
                "client_id": client_id,
                "channel": use_channel,
                "created_at": _now(),
                "last_seen_at": _now(),
                "handoff_count": 0,
            }
            self._data["sessions"][sid] = session
            self._data["active_session_id"] = sid
        self._save()
        return dict(session)

    def handoff(self, *, client_id: str, channel: Optional[str] = None) -> Dict[str, Any]:
        session = self.open_session(client_id=client_id, channel=channel)
        sid = session["session_id"]
        current = self._data["sessions"][sid]
        current["handoff_count"] = int(current.get("handoff_count", 0)) + 1
        current["last_seen_at"] = _now()
        self._save()
        return dict(current)

    def snapshot(self) -> Dict[str, Any]:
        sid = self._data.get("active_session_id")
        return {
            "agent_identity": "ameer",
            "single_agent": True,
            "supported_clients": sorted(SUPPORTED_CLIENTS),
            "supported_channels": sorted(SUPPORTED_CHANNELS),
            "authentication_enabled": self.authentication_enabled,
            "active_session": self._data["sessions"].get(sid) if sid else None,
            "registered_clients": list(self._data["clients"].values()),
        }
