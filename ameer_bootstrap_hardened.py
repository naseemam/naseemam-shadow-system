from __future__ import annotations

from pathlib import Path

import ameer_server
import kernel.repository_execution as repository_execution
from kernel.execution_boundary import ExecutionBoundary
from kernel.executive_kernel import ExecutiveKernel
from kernel.tool_dispatcher import ToolDispatcher


class HardenedRepositoryPolicy(repository_execution.ControlledRepositoryPolicy):
    @staticmethod
    def _normalize(target: str) -> str:
        normalized = str(target or "").strip().replace("\\", "/")
        while normalized.startswith("./"):
            normalized = normalized[2:]
        return normalized


# Harden the policy before any repository executor/validator/auth object is built.
repository_execution.ControlledRepositoryPolicy = HardenedRepositoryPolicy


def _build_repository_kernel() -> ExecutiveKernel:
    repo_root = Path(ameer_server.REPO_ROOT).resolve()
    kernel = ExecutiveKernel(repo_root)
    kernel.permissions.grant(
        "file.create",
        scope=repository_execution.repository_file_create_permission_scope(),
        granted_by="system:controlled_repository_activation",
    )
    kernel.execution_auth = repository_execution.RepositoryExecutionAuthorization(
        repo_root,
        kernel.capabilities,
        kernel.permissions,
    )
    kernel.execution_boundary = ExecutionBoundary(
        approval_gate=kernel.approvals,
        execution_auth=kernel.execution_auth,
    )
    kernel.plan_validator = repository_execution.RepositoryPlanValidator(
        repo_root,
        capability_registry=kernel.capabilities,
        permission_registry=kernel.permissions,
    )
    kernel.file_executor = repository_execution.RepositoryFileExecutor(repo_root)
    kernel.tool_dispatcher = ToolDispatcher(
        tool_registry=kernel.tool_registry,
        execution_boundary=kernel.execution_boundary,
        execution_authorization=kernel.execution_auth,
        approval_gate=kernel.approvals,
        executor=kernel.file_executor.execute,
        shell_executor=kernel.shell_executor.execute,
        workspace_root=repo_root,
    )
    kernel.task_decomposer = repository_execution.RepositoryTaskDecomposer(str(repo_root))
    return kernel


ameer_server.KERNEL = _build_repository_kernel()
ameer_server.EXECUTION_BOUNDARY = ameer_server.KERNEL.execution_boundary
app = ameer_server.app
