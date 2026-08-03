from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import os
import subprocess


WORKSPACE_ROOT = Path(__file__).resolve().parent
ENTRYPOINT = "start_ameer.py"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8011
START_TIME = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def resolve_host() -> str:
    return os.getenv("AMEER_HOST", DEFAULT_HOST)


def resolve_port() -> int:
    raw = os.getenv("AMEER_PORT", str(DEFAULT_PORT)).strip()
    try:
        return int(raw)
    except ValueError:
        return DEFAULT_PORT


def _read_git_commit(workspace_root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(workspace_root),
            capture_output=True,
            text=True,
            check=True,
        )
        commit = (result.stdout or "").strip()
        return commit or "unknown"
    except Exception:
        return "unknown"


COMMIT = _read_git_commit(WORKSPACE_ROOT)
BUILD_ID = os.getenv("AMEER_BUILD_ID") or datetime.now(timezone.utc).strftime("%Y.%m.%d-%H%M")


def runtime_metadata(workspace_root: str | Path | None = None) -> dict:
    root = Path(workspace_root).resolve() if workspace_root else WORKSPACE_ROOT
    return {
        "status": "ok",
        "build": BUILD_ID,
        "build_id": BUILD_ID,
        "commit": COMMIT,
        "workspace": str(root),
        "host": resolve_host(),
        "port": resolve_port(),
        "started_at": START_TIME,
        "pid": os.getpid(),
        "entrypoint": ENTRYPOINT,
    }


def public_runtime_identity(workspace_root: str | Path | None = None) -> dict:
    meta = runtime_metadata(workspace_root=workspace_root)
    return {
        "build": meta["build"],
        "build_id": meta["build_id"],
        "commit": meta["commit"],
        "port": meta["port"],
    }


def runtime_headers(workspace_root: str | Path | None = None) -> dict[str, str]:
    meta = runtime_metadata(workspace_root=workspace_root)
    return {
        "X-Ameer-Build-ID": str(meta["build_id"]),
        "X-Ameer-Commit": str(meta["commit"]),
        "X-Ameer-Port": str(meta["port"]),
    }


def print_runtime_banner(workspace_root: str | Path | None = None) -> None:
    meta = runtime_metadata(workspace_root=workspace_root)
    print("Ameer Runtime")
    print(f"Build: {meta['build']}")
    print(f"Commit: {meta['commit']}")
    print(f"Workspace: {meta['workspace']}")
    print(f"Host: {meta['host']}")
    print(f"Port: {meta['port']}")
    print(f"PID: {meta['pid']}")
    print(f"Started: {meta['started_at']}")
