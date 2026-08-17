from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import os
import subprocess


WORKSPACE_ROOT = Path(__file__).resolve().parent
ENTRYPOINT = "start_ameer.py"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = int(os.getenv("PORT", "8000"))
START_TIME = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def resolve_data_root() -> Path:
    """Return the directory that contains the ``.ameer`` state folder.

    When ``AMEER_DATA_DIR`` is set it must point to the ``.ameer`` directory
    itself (e.g. ``/app/.ameer`` on Railway with a persistent volume mounted
    there).  The function returns the *parent* of that path so that all
    downstream code can continue to use the ``workspace_root / ".ameer"``
    convention unchanged.

    When ``AMEER_DATA_DIR`` is **not** set the function falls back to
    ``WORKSPACE_ROOT`` (the repository checkout directory), which is the
    original behaviour.
    """
    raw = os.getenv("AMEER_DATA_DIR", "").strip()
    if raw:
        data_dir = Path(raw).resolve()
        # AMEER_DATA_DIR is expected to BE the .ameer directory.
        # Return its parent so that `parent / ".ameer"` resolves correctly.
        if data_dir.name == ".ameer":
            return data_dir.parent
        # If the caller passed the parent directly, honour that too.
        return data_dir
    return WORKSPACE_ROOT


def resolve_host() -> str:
    # AMEER_HOST overrides everything; fall back to 0.0.0.0 when a PORT
    # env var is present (Railway, Render, Fly.io set PORT automatically).
    default = "0.0.0.0" if os.getenv("PORT") else DEFAULT_HOST
    return os.getenv("AMEER_HOST", default)


def resolve_port() -> int:
    # Cloud platforms (Railway, Render, Fly.io) inject PORT; respect it.
    raw = os.getenv("AMEER_PORT") or os.getenv("PORT") or str(DEFAULT_PORT)
    try:
        return int(raw.strip())
    except ValueError:
        return DEFAULT_PORT


def _read_git_commit(workspace_root: Path) -> str:
    # Railway exposes the source revision when the service is built from GitHub.
    # Prefer that full SHA because a short local SHA cannot prove deployment identity.
    for key in ("RAILWAY_GIT_COMMIT_SHA", "SOURCE_COMMIT", "GIT_COMMIT_SHA"):
        value = os.getenv(key, "").strip()
        if value:
            return value
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
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
COMMIT_SOURCE = next((key for key in ("RAILWAY_GIT_COMMIT_SHA", "SOURCE_COMMIT", "GIT_COMMIT_SHA") if os.getenv(key, "").strip()), "git")
DEPLOYMENT_ID = os.getenv("RAILWAY_DEPLOYMENT_ID", "").strip()
BUILD_ID = os.getenv("AMEER_BUILD_ID") or DEPLOYMENT_ID or datetime.now(timezone.utc).strftime("%Y.%m.%d-%H%M")


def runtime_metadata(workspace_root: str | Path | None = None) -> dict:
    root = Path(workspace_root).resolve() if workspace_root else WORKSPACE_ROOT
    return {
        "status": "ok",
        "build": BUILD_ID,
        "build_id": BUILD_ID,
        "commit": COMMIT,
        "commit_source": COMMIT_SOURCE,
        "deployment_id": DEPLOYMENT_ID,
        "deployment_provider": "railway" if DEPLOYMENT_ID or COMMIT_SOURCE == "RAILWAY_GIT_COMMIT_SHA" else "unknown",
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
        "commit_source": meta["commit_source"],
        "deployment_id": meta["deployment_id"],
        "started_at": meta["started_at"],
    }


def runtime_headers(workspace_root: str | Path | None = None) -> dict[str, str]:
    meta = runtime_metadata(workspace_root=workspace_root)
    headers = {
        "X-Ameer-Build-ID": str(meta["build_id"]),
        "X-Ameer-Commit": str(meta["commit"]),
    }
    if meta.get("deployment_id"):
        headers["X-Ameer-Deployment-ID"] = str(meta["deployment_id"])
    return headers


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
