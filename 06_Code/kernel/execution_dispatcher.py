"""
execution_dispatcher.py
=======================
Dispatcher for real execution

Ameer says: "سأقوم بـ X" → Creates Job → Calls Tool → Tracks Progress → Reports Result

No more promises - actual execution!
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from kernel.job_system import Job, JobSystem, JobType
from kernel.tool_implementations import get_tool


class ExecutionDispatcher:
    """Dispatch jobs to real tools for actual execution."""

    def __init__(self, workspace_root: str):
        self.job_system = JobSystem(workspace_root)
        self.workspace_root = workspace_root

    async def dispatch_file_read(
        self,
        target: str,
        description: str = "",
        approval_required: bool = False,
    ) -> Dict[str, Any]:
        """Dispatch a file read job."""
        job = self.job_system.create_job(
            job_type=JobType.FILE_OPERATION,
            description=description or f"Read {target}",
            expected_result=f"Content of {target}",
            approval_required=approval_required,
            details={"target": target},
        )

        # Get the tool
        tool = get_tool("file_read")
        if not tool:
            raise ValueError("Tool file_read not found")

        # Execute
        return await self.job_system.execute_job(job, tool)

    async def dispatch_shell_command(
        self,
        command: str,
        description: str = "",
        approval_required: bool = False,
    ) -> Dict[str, Any]:
        """Dispatch a shell command job."""
        job = self.job_system.create_job(
            job_type=JobType.SHELL_COMMAND,
            description=description or f"Execute: {command[:50]}",
            expected_result="Command output",
            approval_required=approval_required,
            details={"command": command},
        )

        # Get the tool
        tool = get_tool("shell_execute")
        if not tool:
            raise ValueError("Tool shell_execute not found")

        # Execute
        return await self.job_system.execute_job(job, tool)

    async def dispatch_browser_navigate(
        self,
        url: str,
        description: str = "",
    ) -> Dict[str, Any]:
        """Dispatch a browser navigate job (always requires approval)."""
        job = self.job_system.create_job(
            job_type=JobType.BROWSER_ACTION,
            description=description or f"Navigate to {url}",
            expected_result="Page loaded",
            approval_required=True,
            details={"url": url},
        )

        tool = get_tool("browser_navigate")
        if not tool:
            raise ValueError("Tool browser_navigate not found")

        return await self.job_system.execute_job(job, tool)

    async def dispatch_github_push(
        self,
        message: str,
        branch: str = "main",
        description: str = "",
    ) -> Dict[str, Any]:
        """Dispatch a GitHub push job (requires approval)."""
        job = self.job_system.create_job(
            job_type=JobType.GITHUB_OPERATION,
            description=description or f"Push to {branch}",
            expected_result="Changes pushed to GitHub",
            approval_required=True,
            details={"message": message, "branch": branch},
        )

        tool = get_tool("github_push")
        if not tool:
            raise ValueError("Tool github_push not found")

        return await self.job_system.execute_job(job, tool)

    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job status."""
        job = self.job_system.get_job(job_id)
        if job:
            return job.to_dict()
        return None
