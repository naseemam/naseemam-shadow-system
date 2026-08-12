"""
executor_shell.py
=================
ShellExecutor — ينفّذ أوامر shell داخل بيئة محكومة ومراقبة.

يعمل هذا المنفذ حصريًا عبر:
    ToolRegistry → ToolDispatcher → ExecutionAuthorization → ExecutionBoundary → ShellExecutor

لا يُستدعى مباشرةً ولا يتجاوز أي طبقة authorization أو approval.
"""

from __future__ import annotations

import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


_DEFAULT_TIMEOUT_SECONDS: int = 60
_MAX_OUTPUT_BYTES: int = 1_048_576  # 1 MB per stream


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class ShellExecutor:
    """
    Executor for controlled shell commands within the runtime workspace.

    Design constraints
    ------------------
    * Commands are executed with shell=False (explicit argv list) to prevent
      injection via untrusted input.  A plain string command is split by the
      caller or accepted as-is via shlex.split.
    * Working directory is always resolved relative to workspace_root and must
      stay inside it (fail-closed on escape attempts).
    * stdout/stderr are captured, truncated at _MAX_OUTPUT_BYTES, and returned
      in a structured result dict — never streamed to an external surface.
    * Execution metadata (start time, duration, cwd, pid) is always included.
    """

    def __init__(
        self,
        workspace_root: Union[str, Path],
        *,
        timeout: int = _DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self._root = Path(workspace_root).resolve()
        self._timeout = int(timeout)

    # ── Public API ────────────────────────────────────────────────────────────

    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a controlled shell command described by *task*.

        Expected keys in *task*
        -----------------------
        command  : str | list[str]  — the command to run (required)
        cwd      : str | None       — working dir relative to workspace_root
        env      : dict | None      — additional environment variables (merged)
        timeout  : int | None       — override default timeout (seconds)
        id       : str | None       — task identifier for tracing

        Returns a result dict with:
            status       : "completed" | "failed" | "timeout" | "blocked"
            stdout       : str
            stderr       : str
            returncode   : int | None
            execution_metadata : dict
        """
        task_id = str(task.get("id") or "<unnamed>")

        # ── 1. Resolve command ──────────────────────────────────────────────
        command = task.get("command")
        if not command:
            return self._error_result(task_id, "missing_command", "No command specified")

        argv = self._parse_command(command)
        if argv is None:
            return self._error_result(task_id, "invalid_command", "Command must be a non-empty string or list")

        # ── 2. Resolve working directory (must stay inside workspace_root) ──
        raw_cwd = task.get("cwd")
        try:
            resolved_cwd = self._resolve_cwd(raw_cwd)
        except ValueError as exc:
            return self._error_result(task_id, "blocked", str(exc))

        # ── 3. Build environment ─────────────────────────────────────────────
        import os
        env = dict(os.environ)
        extra_env = task.get("env") or {}
        if isinstance(extra_env, dict):
            env.update({str(k): str(v) for k, v in extra_env.items()})

        # ── 4. Resolve timeout ───────────────────────────────────────────────
        timeout = task.get("timeout")
        try:
            effective_timeout = int(timeout) if timeout is not None else self._timeout
        except (TypeError, ValueError):
            effective_timeout = self._timeout

        # ── 5. Execute ───────────────────────────────────────────────────────
        start_ts = _now_iso()
        t0 = time.monotonic()
        pid: Optional[int] = None

        try:
            proc = subprocess.Popen(
                argv,
                cwd=str(resolved_cwd),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=False,
            )
            pid = proc.pid
            try:
                raw_stdout, raw_stderr = proc.communicate(timeout=effective_timeout)
                returncode = proc.returncode
                timed_out = False
            except subprocess.TimeoutExpired:
                proc.kill()
                raw_stdout, raw_stderr = proc.communicate()
                returncode = proc.returncode
                timed_out = True
        except FileNotFoundError:
            duration_ms = int((time.monotonic() - t0) * 1000)
            return self._error_result(
                task_id,
                "failed",
                f"Command not found: {argv[0]}",
                execution_metadata={
                    "task_id": task_id,
                    "start_time": start_ts,
                    "duration_ms": duration_ms,
                    "cwd": str(resolved_cwd),
                    "pid": None,
                    "timed_out": False,
                },
            )
        except Exception as exc:
            duration_ms = int((time.monotonic() - t0) * 1000)
            return self._error_result(
                task_id,
                "failed",
                str(exc),
                execution_metadata={
                    "task_id": task_id,
                    "start_time": start_ts,
                    "duration_ms": duration_ms,
                    "cwd": str(resolved_cwd),
                    "pid": pid,
                    "timed_out": False,
                },
            )

        duration_ms = int((time.monotonic() - t0) * 1000)
        stdout = self._decode_output(raw_stdout)
        stderr = self._decode_output(raw_stderr)

        if timed_out:
            status = "timeout"
        elif returncode == 0:
            status = "completed"
        else:
            status = "failed"

        return {
            "task_id": task_id,
            "status": status,
            "stdout": stdout,
            "stderr": stderr,
            "returncode": returncode,
            "execution_metadata": {
                "task_id": task_id,
                "start_time": start_ts,
                "duration_ms": duration_ms,
                "cwd": str(resolved_cwd.relative_to(self._root)).replace("\\", "/"),
                "pid": pid,
                "timed_out": timed_out,
            },
        }

    # ── Private helpers ───────────────────────────────────────────────────────

    def _resolve_cwd(self, raw_cwd: Optional[str]) -> Path:
        """Resolve working directory; must remain inside workspace_root."""
        if raw_cwd is None:
            return self._root

        candidate = Path(raw_cwd.strip())
        resolved = (
            candidate.resolve()
            if candidate.is_absolute()
            else (self._root / candidate).resolve()
        )
        if not resolved.is_relative_to(self._root):
            raise ValueError(
                f"cwd '{raw_cwd}' resolves outside workspace_root — blocked"
            )
        return resolved

    @staticmethod
    def _parse_command(command: Any) -> Optional[List[str]]:
        """Convert command to argv list; return None on invalid input."""
        if isinstance(command, list):
            flat = [str(c) for c in command if c is not None]
            return flat if flat else None
        if isinstance(command, str) and command.strip():
            import shlex
            try:
                return shlex.split(command)
            except ValueError:
                return [command]
        return None

    @staticmethod
    def _decode_output(raw: bytes) -> str:
        """Decode bytes, truncate, and return as UTF-8 string."""
        truncated = raw[:_MAX_OUTPUT_BYTES]
        try:
            return truncated.decode("utf-8", errors="replace")
        except Exception:
            return repr(truncated)

    @staticmethod
    def _error_result(
        task_id: str,
        status: str,
        reason: str,
        *,
        execution_metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return {
            "task_id": task_id,
            "status": status,
            "stdout": "",
            "stderr": "",
            "returncode": None,
            "reason": reason,
            "execution_metadata": execution_metadata or {},
        }
