import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "06_Code"))

from kernel.tool_implementations import shell_execute_tool


class _Job:
    def __init__(self, details):
        self.details = details
        self.progress = 0
        self.progress_message = ""


def test_shell_tool_never_uses_a_shell():
    source = (ROOT / "06_Code" / "kernel" / "tool_implementations.py").read_text(encoding="utf-8")
    start = source.index("async def shell_execute_tool")
    end = source.index("# BROWSER TOOLS")
    implementation = source[start:end]
    assert "shell=True" not in implementation
    assert "shell=False" in implementation


def test_shell_tool_executes_simple_argv_and_rejects_shell_operators():
    safe = asyncio.run(shell_execute_tool(_Job({"argv": ["echo", "safe"]})))
    assert safe["success"] is True
    assert safe["argv"] == ["echo", "safe"]

    try:
        asyncio.run(shell_execute_tool(_Job({"command": "echo safe && id"})))
    except ValueError as exc:
        assert "Shell operators" in str(exc)
    else:
        raise AssertionError("shell operators must be rejected")


def test_railway_config_has_healthcheck_and_launcher_imports_os():
    railway = (ROOT / "railway.toml").read_text(encoding="utf-8")
    launcher = (ROOT / "start_ameer.py").read_text(encoding="utf-8")
    assert 'healthcheckPath = "/health"' in railway
    assert "healthcheckTimeout = 120" in railway
    assert "import os" in launcher
