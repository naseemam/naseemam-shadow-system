"""
job_system.py
=============
Real Job/Tool execution system

Every operation gets a unique Job ID that can be tracked:
- Job created with ID
- Tool/function invoked with Job context
- Progress tracked
- Result recorded
- History maintained
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional, List, Callable, Awaitable


class JobStatus(Enum):
    """Job execution status."""
    CREATED = "created"           # Job created, not started
    PENDING = "pending"           # Waiting for approval
    APPROVED = "approved"         # Approved, ready to run
    RUNNING = "running"           # Currently executing
    SUCCESS = "success"           # Completed successfully
    FAILED = "failed"             # Failed with error
    CANCELLED = "cancelled"       # Cancelled by founder


class JobType(Enum):
    """Type of job."""
    FILE_OPERATION = "file_operation"
    SHELL_COMMAND = "shell_command"
    BROWSER_ACTION = "browser_action"
    GITHUB_OPERATION = "github_operation"
    EMAIL_OPERATION = "email_operation"
    GOOGLE_OPERATION = "google_operation"
    SLACK_MESSAGE = "slack_message"
    RAILWAY_DEPLOY = "railway_deploy"
    API_CALL = "api_call"
    DATA_ANALYSIS = "data_analysis"


class Job:
    """A trackable Job with ID."""

    def __init__(
        self,
        job_type: JobType,
        description: str,
        expected_result: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.id = str(uuid.uuid4())
        self.job_type = job_type
        self.description = description
        self.expected_result = expected_result
        self.details = details or {}
        self.status = JobStatus.CREATED
        self.approval_required = False
        self.approved_by = None
        self.approved_at = None
        self.started_at = None
        self.ended_at = None
        self.result = None
        self.error = None
        self.progress = 0  # 0-100
        self.progress_message = ""
        self.created_at = datetime.now(timezone.utc).isoformat() + "Z"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "job_type": self.job_type.value,
            "description": self.description,
            "expected_result": self.expected_result,
            "details": self.details,
            "status": self.status.value,
            "approval_required": self.approval_required,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "result": self.result,
            "error": self.error,
            "progress": self.progress,
            "progress_message": self.progress_message,
            "created_at": self.created_at,
        }


class JobSystem:
    """Manage and track jobs."""

    def __init__(self, workspace_root: str | Path):
        self._root = Path(workspace_root).resolve()
        self._ameer_dir = self._root / ".ameer"
        self._state_file = self._ameer_dir / "state.json"
        self._ensure_state_file()

    def _ensure_state_file(self) -> None:
        """Ensure state.json exists."""
        if not self._state_file.exists():
            self._ameer_dir.mkdir(parents=True, exist_ok=True)
            initial_state = {
                "jobs": [],
                "running_tasks": [],
                "pending_operations": [],
                "browser_pending_actions": [],
            }
            with open(self._state_file, 'w', encoding='utf-8') as f:
                json.dump(initial_state, f, indent=2, ensure_ascii=False)

    def create_job(
        self,
        job_type: JobType,
        description: str,
        expected_result: str,
        approval_required: bool = False,
        details: Optional[Dict[str, Any]] = None,
    ) -> Job:
        """Create a new Job."""
        job = Job(
            job_type=job_type,
            description=description,
            expected_result=expected_result,
            details=details,
        )
        job.approval_required = approval_required
        job.status = JobStatus.PENDING if approval_required else JobStatus.APPROVED

        # Save to state
        self._save_job(job)

        return job

    def _save_job(self, job: Job) -> None:
        """Save job to state.json."""
        try:
            with open(self._state_file, 'r', encoding='utf-8') as f:
                state = json.load(f)

            # Check if job exists and update, else append
            jobs = state.get("jobs", [])
            found = False
            for i, j in enumerate(jobs):
                if j.get("id") == job.id:
                    jobs[i] = job.to_dict()
                    found = True
                    break

            if not found:
                jobs.append(job.to_dict())

            state["jobs"] = jobs

            with open(self._state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving job: {e}")

    async def execute_job(
        self,
        job: Job,
        tool_func: Callable[..., Awaitable[Dict[str, Any]]],
    ) -> Dict[str, Any]:
        """Execute a job with a tool function."""

        # Update status to RUNNING
        job.status = JobStatus.RUNNING
        job.started_at = datetime.now(timezone.utc).isoformat() + "Z"
        job.progress = 0
        job.progress_message = "Starting..."
        self._save_job(job)

        try:
            # Call the tool function with job context
            result = await tool_func(job)

            # Success
            job.status = JobStatus.SUCCESS
            job.result = result
            job.progress = 100
            job.progress_message = "Completed successfully"
            job.ended_at = datetime.now(timezone.utc).isoformat() + "Z"
            self._save_job(job)

            return {
                "success": True,
                "job_id": job.id,
                "result": result,
            }

        except Exception as e:
            # Failed
            job.status = JobStatus.FAILED
            job.error = str(e)
            job.progress = 0
            job.progress_message = f"Failed: {str(e)}"
            job.ended_at = datetime.now(timezone.utc).isoformat() + "Z"
            self._save_job(job)

            return {
                "success": False,
                "job_id": job.id,
                "error": str(e),
            }

    def get_job(self, job_id: str) -> Optional[Job]:
        """Get job by ID."""
        try:
            with open(self._state_file, 'r', encoding='utf-8') as f:
                state = json.load(f)

            for job_dict in state.get("jobs", []):
                if job_dict.get("id") == job_id:
                    # Reconstruct Job object
                    job = Job(
                        job_type=JobType(job_dict.get("job_type")),
                        description=job_dict.get("description", ""),
                        expected_result=job_dict.get("expected_result", ""),
                        details=job_dict.get("details", {}),
                    )
                    job.id = job_dict.get("id")
                    job.status = JobStatus(job_dict.get("status", "created"))
                    job.result = job_dict.get("result")
                    job.error = job_dict.get("error")
                    return job
        except Exception:
            pass

        return None

    def get_running_jobs(self) -> List[Job]:
        """Get all running jobs."""
        try:
            with open(self._state_file, 'r', encoding='utf-8') as f:
                state = json.load(f)

            jobs = []
            for job_dict in state.get("jobs", []):
                if job_dict.get("status") == JobStatus.RUNNING.value:
                    job = Job(
                        job_type=JobType(job_dict.get("job_type")),
                        description=job_dict.get("description", ""),
                        expected_result=job_dict.get("expected_result", ""),
                    )
                    job.id = job_dict.get("id")
                    jobs.append(job)

            return jobs
        except Exception:
            return []
