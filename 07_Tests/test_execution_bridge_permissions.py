from __future__ import annotations

import sys
from pathlib import Path

CODE_ROOT = Path(__file__).resolve().parents[1] / "06_Code"
if str(CODE_ROOT) not in sys.path:
    sys.path.insert(0, str(CODE_ROOT))

from kernel.agent_operations import AgentOperations, AgentTaskDecomposer
from kernel.execution_bridge_patch import install_execution_bridge_patch
from kernel.repository_execution import (
    ControlledRepositoryPolicy,
    repository_file_create_permission_scope,
    repository_file_read_permission_scope,
)


def test_repository_read_and_write_scopes_are_controlled_and_distinct() -> None:
    read_scope = repository_file_read_permission_scope()
    write_scope = repository_file_create_permission_scope()
    assert '"tool_name": "file.read"' in read_scope
    assert '"action": "read"' in read_scope
    assert '"scope_kind": "controlled_repository"' in read_scope
    assert '"tool_name": "file.create"' in write_scope
    assert read_scope != write_scope


def test_founder_delegated_repository_policy_allows_all_internal_paths(tmp_path: Path) -> None:
    policy = ControlledRepositoryPolicy(tmp_path)
    assert policy.is_allowed("09_Assets/web/index.html")
    assert policy.is_allowed("06_Code/kernel/example.py")
    assert policy.is_allowed(".env")
    assert policy.is_allowed(".github/workflows/deploy.yml")
    assert policy.is_allowed(".ameer/state.json")
    assert not policy.is_allowed("../outside.txt")


def test_natural_ui_command_enters_real_execution_lane(tmp_path: Path) -> None:
    install_execution_bridge_patch()
    decomposer = AgentTaskDecomposer(str(tmp_path), AgentOperations(tmp_path))
    result = decomposer.decompose("عدل الواجهه وكمل صندوق الدردشه واربط الازرار")
    assert result["intent"] == "build_homepage"
    assert result.get("execution_bridge") == "natural_ui_command"
    targets = [str(task.get("target") or "") for task in result.get("tasks") or []]
    assert "09_Assets/web/index.html" in targets
    html = next(str(task.get("content") or "") for task in result["tasks"] if str(task.get("target") or "").endswith("index.html"))
    assert "ameer-chat-panel" in html
    assert "ameerChatForm" in html


def test_short_followup_reuses_last_actionable_stage(tmp_path: Path) -> None:
    install_execution_bridge_patch()
    decomposer = AgentTaskDecomposer(str(tmp_path), AgentOperations(tmp_path))
    first = decomposer.decompose("عدل الواجهة الرئيسية وكمل صندوق الدردشة")
    assert first["intent"] == "build_homepage"
    followup = decomposer.decompose("خلصها واختبر")
    assert followup["intent"] == "build_homepage"
    assert followup.get("execution_bridge") == "stage_continuation"
