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
