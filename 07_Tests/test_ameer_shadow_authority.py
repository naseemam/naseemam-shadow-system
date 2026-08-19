import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "06_Code"))

from kernel.ameer_authority import (
    approval_actions,
    canonical_creation_action,
    policy_snapshot,
    requires_founder_approval,
)
from kernel.approval_gate import ApprovalGate
from kernel.execution_boundary import BoundaryVerdict, ExecutionBoundary


class ApprovedAuthorization:
    def check(self, **_kwargs):
        return {"status": "approved", "request_id": "delegated-execution"}


def test_only_the_four_new_root_assets_require_founder_approval():
    assert tuple(approval_actions()) == (
        "create_site",
        "create_program",
        "create_system",
        "create_repository",
    )
    for action in approval_actions():
        assert requires_founder_approval(action) is True

    for delegated_action in (
        "delete",
        "publish",
        "deploy",
        "rollback",
        "email.send",
        "trading.execute",
        "worker.create",
        "page.create",
        "repository.write",
    ):
        assert requires_founder_approval(delegated_action) is False, delegated_action


def test_creation_aliases_and_existing_asset_context_are_resolved_correctly():
    assert canonical_creation_action("website.create") == "create_site"
    assert canonical_creation_action("github.create_repository") == "create_repository"
    assert canonical_creation_action("create", {"asset_kind": "نظام"}) == "create_system"
    assert canonical_creation_action("create_site", {"within_existing_asset": True}) is None
    assert canonical_creation_action("create", {"asset_kind": "program", "creation_scope": "component"}) is None


def test_approval_gate_exposes_the_same_four_root_creation_actions():
    with tempfile.TemporaryDirectory() as workspace:
        gate = ApprovalGate(workspace)
        for action in approval_actions():
            assert gate.requires_approval(action) is True
        for delegated_action in ("delete", "publish", "deploy", "rollback", "external", "financial"):
            assert gate.requires_approval(delegated_action) is False


def test_execution_boundary_allows_existing_asset_execution_without_approval_gate():
    boundary = ExecutionBoundary(execution_auth=ApprovedAuthorization())
    for action in ("delete", "publish", "deploy", "rollback", "email.send"):
        result = boundary.evaluate(
            guardian={"status": "pass"},
            request_type="execution",
            intent="build_homepage",
            action=action,
            context={"existing_asset": True},
        )
        assert result.verdict == BoundaryVerdict.ALLOW, action


def test_execution_boundary_opens_a_gate_only_for_new_root_assets():
    with tempfile.TemporaryDirectory() as workspace:
        boundary = ExecutionBoundary(
            approval_gate=ApprovalGate(workspace),
            execution_auth=ApprovedAuthorization(),
        )
        result = boundary.evaluate(
            guardian={"status": "pass"},
            request_type="execution",
            intent="build_homepage",
            action="create",
            context={"asset_kind": "site", "asset_name": "موقع المدرسة"},
        )
        assert result.verdict == BoundaryVerdict.PENDING
        assert result.reason == "approval_gate_created"


def test_policy_snapshot_is_safe_and_user_visible():
    snapshot = policy_snapshot()
    assert snapshot["mode"] == "autonomous_with_root_asset_creation_gate"
    assert snapshot["autonomous_within_existing_assets"] is True
    assert snapshot["approval_actions"] == list(approval_actions())
    assert len(snapshot["approval_gates"]) == 4


def test_authority_endpoint_and_shadow_ui_expose_the_same_policy():
    from fastapi.testclient import TestClient
    from ameer_server import app

    client = TestClient(app)
    response = client.get("/authority")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["authority"]["approval_actions"] == list(approval_actions())

    index = (ROOT / "09_Assets" / "web" / "index.html").read_text(encoding="utf-8")
    assert 'id="authority"' in index
    assert "سلطة أمير التنفيذية" in index
    for label in ("موقع جديد", "برنامج جديد", "نظام جديد", "مستودع جديد"):
        assert label in index


def test_task_decomposer_marks_all_four_root_asset_requests_for_owner_approval():
    from kernel.task_decomposer import TaskDecomposer

    decomposer = TaskDecomposer(str(ROOT))
    commands = {
        "أنشئ موقع جديد للمدرسة": "create_site",
        "أنشئ برنامج جديد للحجوزات": "create_program",
        "أنشئ نظام جديد للموظفات": "create_system",
        "أنشئ مستودع جديد للمشروع": "create_repository",
    }
    for command, approval_action in commands.items():
        result = decomposer.decompose(command)
        assert result["requires_approval"] is True
        assert result["permission_mode"] == "root_asset_creation"
        assert result["approval_action"] == approval_action
