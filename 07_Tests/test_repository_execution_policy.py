from pathlib import Path

from kernel.repository_execution import ControlledRepositoryPolicy


def test_founder_delegated_repository_policy_allows_all_internal_paths(tmp_path: Path):
    policy = ControlledRepositoryPolicy(tmp_path)

    allowed = [
        "09_Assets/web/index.html",
        "09_Assets/runtime_workspace/home/index.html",
        "06_Code/kernel/example.py",
        "07_Tests/test_example.py",
        "ameer_server.py",
        ".env",
        ".env.production",
        ".github/workflows/ci.yml",
        ".git/config",
        ".ameer/state.json",
        "08_Backups/recovery.json",
    ]
    for target in allowed:
        assert policy.is_allowed(target), target


def test_founder_delegated_repository_policy_denies_only_escape_paths(tmp_path: Path):
    policy = ControlledRepositoryPolicy(tmp_path)

    for target in ("../outside.txt", "/etc/passwd", "./../outside.txt", "../../.env"):
        assert not policy.is_allowed(target), target


def test_repository_kernel_allows_full_internal_write_but_not_escape(tmp_path: Path):
    from kernel.execution_boundary import ExecutionBoundary
    from kernel.executive_kernel import ExecutiveKernel
    from kernel.repository_execution import (
        RepositoryExecutionAuthorization,
        RepositoryFileExecutor,
        repository_file_create_permission_scope,
    )
    from kernel.tool_dispatcher import ToolDispatcher

    kernel = ExecutiveKernel(tmp_path)
    kernel.permissions.grant(
        "file.create",
        scope=repository_file_create_permission_scope(),
        granted_by="test:founder_full_repository_authority",
    )
    authorization = RepositoryExecutionAuthorization(tmp_path, kernel.capabilities, kernel.permissions)
    dispatcher = ToolDispatcher(
        tool_registry=kernel.tool_registry,
        execution_boundary=ExecutionBoundary(approval_gate=kernel.approvals, execution_auth=authorization),
        execution_authorization=authorization,
        approval_gate=kernel.approvals,
        executor=RepositoryFileExecutor(tmp_path).execute,
        workspace_root=tmp_path,
    )

    for target in ("09_Assets/web/index.html", ".env", ".github/workflows/ci.yml", ".ameer/state.json"):
        written = dispatcher.dispatch(
            tool_name="file.create",
            context={
                "target": target,
                "content": f"updated: {target}",
                "executor_payload": {"target": target, "content": f"updated: {target}"},
            },
            guardian={"status": "pass"},
            request_type="execution",
            intent="build_homepage",
        )
        assert written["decision"] == "ALLOW", target
        assert (tmp_path / target).read_text(encoding="utf-8") == f"updated: {target}"

    denied = dispatcher.dispatch(
        tool_name="file.create",
        context={
            "target": "../outside.txt",
            "content": "blocked",
            "executor_payload": {"target": "../outside.txt", "content": "blocked"},
        },
        guardian={"status": "pass"},
        request_type="execution",
        intent="build_homepage",
    )
    assert denied["decision"] == "DENY"
