from __future__ import annotations

from pathlib import Path

import ameer_server
from kernel.delivery_execution import DeliveryExecutiveKernel
from kernel.execution_boundary import ExecutionBoundary
from kernel.repository_execution import (
    RepositoryExecutionAuthorization,
    RepositoryFileExecutor,
    RepositoryPlanValidator,
    RepositoryTaskDecomposer,
    repository_file_create_permission_scope,
)
from kernel.tool_dispatcher import ToolDispatcher


def _build_kernel() -> DeliveryExecutiveKernel:
    repo_root = Path(ameer_server.REPO_ROOT).resolve()
    kernel = DeliveryExecutiveKernel(repo_root)
    kernel.permissions.grant(
        "file.create",
        scope=repository_file_create_permission_scope(),
        granted_by="system:controlled_repository_activation",
    )
    kernel.execution_auth = RepositoryExecutionAuthorization(
        repo_root,
        kernel.capabilities,
        kernel.permissions,
    )
    kernel.execution_boundary = ExecutionBoundary(
        approval_gate=kernel.approvals,
        execution_auth=kernel.execution_auth,
    )
    kernel.plan_validator = RepositoryPlanValidator(
        repo_root,
        capability_registry=kernel.capabilities,
        permission_registry=kernel.permissions,
    )
    kernel.file_executor = RepositoryFileExecutor(repo_root)
    kernel.tool_dispatcher = ToolDispatcher(
        tool_registry=kernel.tool_registry,
        execution_boundary=kernel.execution_boundary,
        execution_authorization=kernel.execution_auth,
        approval_gate=kernel.approvals,
        executor=kernel.file_executor.execute,
        shell_executor=kernel.shell_executor.execute,
        workspace_root=repo_root,
    )
    kernel.task_decomposer = RepositoryTaskDecomposer(str(repo_root))
    return kernel


# One runtime kernel owns both controlled local writes and explicit external delivery.
ameer_server.KERNEL = _build_kernel()
ameer_server.EXECUTION_BOUNDARY = ameer_server.KERNEL.execution_boundary
app = ameer_server.app
