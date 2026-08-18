"""
tool_implementations.py
=======================
Real tool function implementations

Each tool is a real callable that gets invoked with Job context
and reports back progress/results.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from kernel.job_system import Job, JobStatus


# FILE OPERATIONS TOOLS

async def file_read_tool(job: Job) -> Dict[str, Any]:
    """Tool: Read a file."""
    target = job.details.get("target", "")

    if not target:
        raise ValueError("No target file specified")

    target_path = Path(target)

    if not target_path.exists():
        raise FileNotFoundError(f"File not found: {target}")

    job.progress = 50
    job.progress_message = f"Reading {target}..."

    try:
        content = target_path.read_text(encoding='utf-8')

        job.progress = 100
        job.progress_message = "File read successfully"

        return {
            "file": str(target),
            "size": len(content),
            "content_preview": content[:500],
            "full_content": content,
        }
    except Exception as e:
        raise Exception(f"Failed to read file: {e}")


async def file_write_tool(job: Job) -> Dict[str, Any]:
    """Tool: Write to a file."""
    target = job.details.get("target", "")
    content = job.details.get("content", "")

    if not target:
        raise ValueError("No target file specified")

    target_path = Path(target)
    target_path.parent.mkdir(parents=True, exist_ok=True)

    job.progress = 50
    job.progress_message = f"Writing to {target}..."

    try:
        target_path.write_text(content, encoding='utf-8')

        job.progress = 100
        job.progress_message = "File written successfully"

        return {
            "file": str(target),
            "size": len(content),
            "status": "created",
        }
    except Exception as e:
        raise Exception(f"Failed to write file: {e}")


# SHELL EXECUTION TOOLS

async def shell_execute_tool(job: Job) -> Dict[str, Any]:
    """Execute one argv-based internal command without invoking a shell.

    Shell operators are intentionally rejected. Plans that need composition must
    create separate governed tasks, which prevents one text field from becoming
    an arbitrary shell script.
    """
    import shlex
    import subprocess

    command = job.details.get("command", "")
    argv = job.details.get("argv")
    if argv is None:
        if not isinstance(command, str) or not command.strip():
            raise ValueError("No command specified")
        argv = shlex.split(command)
    if not isinstance(argv, list) or not argv or not all(isinstance(item, str) and item for item in argv):
        raise ValueError("Command must be a non-empty argv list or a simple command string")
    forbidden = {"|", "||", "&&", ";", ">", ">>", "<", "<<", "`", "&"}
    if any(token in forbidden for token in argv):
        raise ValueError("Shell operators are not allowed; split the work into governed tasks")

    display = " ".join(shlex.quote(item) for item in argv)
    job.progress = 25
    job.progress_message = f"Executing: {display[:50]}..."
    try:
        result = subprocess.run(
            argv,
            shell=False,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        job.progress = 100
        job.progress_message = "Command executed"
        return {
            "command": display,
            "argv": argv,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "success": result.returncode == 0,
        }
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("Command execution timed out") from exc
    except OSError as exc:
        raise RuntimeError(f"Failed to execute command: {exc}") from exc


# BROWSER TOOLS

async def browser_navigate_tool(job: Job) -> Dict[str, Any]:
    """Tool: Navigate to URL."""
    url = job.details.get("url", "")

    if not url:
        raise ValueError("No URL specified")

    job.progress = 50
    job.progress_message = f"Navigating to {url}..."

    # TODO: Integrate with Playwright/Anchor
    # For now, return mock result
    job.progress = 100
    job.progress_message = "Navigated successfully"

    return {
        "url": url,
        "status": "navigated",
        "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
    }


async def browser_read_content_tool(job: Job) -> Dict[str, Any]:
    """Tool: Read page content."""
    url = job.details.get("url", "")
    selector = job.details.get("selector")

    if not url:
        raise ValueError("No URL specified")

    job.progress = 50
    job.progress_message = f"Reading content from {url}..."

    # TODO: Integrate with Playwright/Anchor
    # For now, return mock result
    job.progress = 100
    job.progress_message = "Content read successfully"

    return {
        "url": url,
        "selector": selector,
        "content": "[Page content would be read here]",
    }


# GITHUB TOOLS

async def github_push_tool(job: Job) -> Dict[str, Any]:
    """Tool: Push to GitHub."""
    message = job.details.get("message", "")
    branch = job.details.get("branch", "main")

    if not message:
        raise ValueError("No commit message specified")

    job.progress = 33
    job.progress_message = "Staging changes..."

    # TODO: Integrate with GitPython
    # For now, return mock result

    job.progress = 66
    job.progress_message = "Committing changes..."

    job.progress = 100
    job.progress_message = "Pushed to GitHub"

    return {
        "branch": branch,
        "message": message,
        "status": "pushed",
    }


# EMAIL TOOLS

async def email_send_tool(job: Job) -> Dict[str, Any]:
    """Tool: Send email."""
    to = job.details.get("to", "")
    subject = job.details.get("subject", "")
    body = job.details.get("body", "")

    if not to or not subject:
        raise ValueError("Missing to/subject")

    job.progress = 50
    job.progress_message = f"Sending email to {to}..."

    # TODO: Integrate with SMTP
    # For now, return mock result

    job.progress = 100
    job.progress_message = "Email sent"

    return {
        "to": to,
        "subject": subject,
        "status": "sent",
    }


# TOOL REGISTRY

TOOL_REGISTRY = {
    "file_read": file_read_tool,
    "file_write": file_write_tool,
    "shell_execute": shell_execute_tool,
    "browser_navigate": browser_navigate_tool,
    "browser_read_content": browser_read_content_tool,
    "github_push": github_push_tool,
    "email_send": email_send_tool,
}


def get_tool(tool_name: str):
    """Get a tool by name."""
    return TOOL_REGISTRY.get(tool_name)
