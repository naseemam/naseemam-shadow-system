from pathlib import Path

from kernel.repository_execution import ControlledRepositoryPolicy


def test_controlled_repository_policy_allows_expected_paths(tmp_path: Path):
    policy = ControlledRepositoryPolicy(tmp_path)

    assert policy.is_allowed("09_Assets/web/index.html")
    assert policy.is_allowed("09_Assets/runtime_workspace/home/index.html")
    assert policy.is_allowed("06_Code/kernel/example.py")
    assert policy.is_allowed("07_Tests/test_example.py")
    assert policy.is_allowed("ameer_server.py")


def test_controlled_repository_policy_denies_sensitive_and_escape_paths(tmp_path: Path):
    policy = ControlledRepositoryPolicy(tmp_path)

    denied = [
        ".git/config",
        ".github/workflows/deploy.yml",
        ".ameer/state.json",
        "08_Backups/secret.txt",
        ".env",
        ".env.production",
        "../outside.txt",
        "/etc/passwd",
        "./../outside.txt",
    ]

    for target in denied:
        assert not policy.is_allowed(target), target


def test_repository_kernel_allows_shadow_ui_write_only_within_controlled_scope(tmp_path: Path):
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
        granted_by="test:controlled_repository",
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

    allowed = dispatcher.dispatch(
        tool_name="file.create",
        context={
            "target": "09_Assets/web/index.html",
            "content": "<main>نظام الظل</main>",
            "executor_payload": {"target": "09_Assets/web/index.html", "content": "<main>نظام الظل</main>"},
        },
        guardian={"status": "pass"},
        request_type="execution",
        intent="build_homepage",
    )
    assert allowed["decision"] == "ALLOW"
    assert (tmp_path / "09_Assets/web/index.html").read_text(encoding="utf-8") == "<main>نظام الظل</main>"

    denied = dispatcher.dispatch(
        tool_name="file.create",
        context={
            "target": ".env",
            "content": "SECRET=blocked",
            "executor_payload": {"target": ".env", "content": "SECRET=blocked"},
        },
        guardian={"status": "pass"},
        request_type="execution",
        intent="build_homepage",
    )
    assert denied["decision"] == "DENY"
    assert denied["reason"] == "execution_authorization_denied"
