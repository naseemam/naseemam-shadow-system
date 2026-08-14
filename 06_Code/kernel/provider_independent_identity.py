from __future__ import annotations

import json
import os
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, Optional


class ProviderIndependentIdentity:
    """Persistent identity layer for Ameer, independent of model/provider.

    The provider/model is an execution engine, not the identity owner. Ameer
    keeps one stable identity, memory namespace, policy profile and continuity
    record across devices, channels, providers and model upgrades.
    """

    IDENTITY_ID = "ameer"
    DISPLAY_NAME = "أمير"
    ROLE = "executive_agent"

    def __init__(self, workspace_root: str | Path) -> None:
        root = Path(os.getenv("AMEER_DATA_DIR") or workspace_root).resolve()
        root.mkdir(parents=True, exist_ok=True)
        self.db_path = root / "provider_independent_identity.sqlite3"
        self._init_db()
        self._ensure_identity()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS identity_profile (
              identity_id TEXT PRIMARY KEY,
              display_name TEXT NOT NULL,
              role TEXT NOT NULL,
              constitution_version TEXT NOT NULL,
              style_profile_json TEXT NOT NULL,
              policy_profile_json TEXT NOT NULL,
              created_at REAL NOT NULL,
              updated_at REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS provider_sessions (
              provider TEXT NOT NULL,
              model TEXT NOT NULL,
              first_seen REAL NOT NULL,
              last_seen REAL NOT NULL,
              PRIMARY KEY(provider, model)
            );
            """)

    def _ensure_identity(self) -> None:
        now = time.time()
        style = {
            "languages": ["ar-SA", "ar", "en"],
            "arabic_modes": ["saudi_colloquial", "gulf_colloquial", "msa"],
            "contextual_short_commands": True,
            "accept_incomplete_phrases_when_context_is_clear": True,
            "identity_changes_with_provider": False,
        }
        policy = {
            "founder_is_final_authority": True,
            "approval_model": "final_gate_only",
            "provider_is_replaceable_engine": True,
            "memory_is_provider_independent": True,
            "capabilities_are_provider_independent": True,
            "device_and_channel_continuity": True,
        }
        with self._connect() as db:
            db.execute(
                "INSERT OR IGNORE INTO identity_profile(identity_id, display_name, role, constitution_version, style_profile_json, policy_profile_json, created_at, updated_at) VALUES(?,?,?,?,?,?,?,?)",
                (
                    self.IDENTITY_ID,
                    self.DISPLAY_NAME,
                    self.ROLE,
                    "1.0",
                    json.dumps(style, ensure_ascii=False),
                    json.dumps(policy, ensure_ascii=False),
                    now,
                    now,
                ),
            )

    def record_engine(self, provider: str, model: str) -> Dict[str, Any]:
        provider = (provider or "unknown").strip().lower()
        model = (model or "unknown").strip()
        now = time.time()
        with self._connect() as db:
            row = db.execute(
                "SELECT first_seen FROM provider_sessions WHERE provider=? AND model=?",
                (provider, model),
            ).fetchone()
            if row:
                db.execute(
                    "UPDATE provider_sessions SET last_seen=? WHERE provider=? AND model=?",
                    (now, provider, model),
                )
            else:
                db.execute(
                    "INSERT INTO provider_sessions(provider, model, first_seen, last_seen) VALUES(?,?,?,?)",
                    (provider, model, now, now),
                )
        return {"identity": self.IDENTITY_ID, "provider": provider, "model": model}

    def profile(self) -> Dict[str, Any]:
        with self._connect() as db:
            row = db.execute(
                "SELECT * FROM identity_profile WHERE identity_id=?",
                (self.IDENTITY_ID,),
            ).fetchone()
            engines = db.execute(
                "SELECT provider, model, first_seen, last_seen FROM provider_sessions ORDER BY last_seen DESC"
            ).fetchall()
        return {
            "identity_id": row["identity_id"],
            "display_name": row["display_name"],
            "role": row["role"],
            "constitution_version": row["constitution_version"],
            "style_profile": json.loads(row["style_profile_json"]),
            "policy_profile": json.loads(row["policy_profile_json"]),
            "known_engines": [dict(item) for item in engines],
            "identity_owner": "ameer_core",
            "provider_role": "replaceable_execution_engine",
        }

    def build_identity_context(self, provider: Optional[str] = None, model: Optional[str] = None) -> Dict[str, Any]:
        if provider or model:
            self.record_engine(provider or "unknown", model or "unknown")
        profile = self.profile()
        return {
            "name": profile["display_name"],
            "identity_id": profile["identity_id"],
            "role": profile["role"],
            "instruction": (
                "You are operating as Ameer. The current model/provider is only an execution engine. "
                "Do not redefine Ameer's identity, authority, memory ownership, approval policy, or relationship with the Founder."
            ),
            "style_profile": profile["style_profile"],
            "policy_profile": profile["policy_profile"],
        }
