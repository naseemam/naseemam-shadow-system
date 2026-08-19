from pathlib import Path

import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "06_Code"))

from kernel.expanded_agent import ExpandedAgentExecutiveKernel
from kernel.task_decomposer import TaskDecomposer


def _stage(trace):
    return trace["pipeline"][0]["stage"]


def test_design_website_phrase_is_internal_execution_intent():
    result = TaskDecomposer(ROOT).decompose("صمم موقعاً حديثاً للمركز")
    assert result["intent"] == "build_website"
    assert result["task_count"] == 3
    assert result["requires_approval"] is False


def test_delete_inside_existing_asset_executes_without_chat_final_approval():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        target = root / "09_Assets" / "web" / "removable.txt"
        target.parent.mkdir(parents=True)
        target.write_text("delete me", encoding="utf-8")
        agent = ExpandedAgentExecutiveKernel(root)

        trace = agent.execute_command("احذف ملف 09_Assets/web/removable.txt")

        assert _stage(trace) == "delete"
        assert trace["final"]["accepted"] is True
        assert not target.exists()


def test_deploy_inside_existing_asset_executes_without_chat_final_approval():
    with tempfile.TemporaryDirectory() as tmp:
        agent = ExpandedAgentExecutiveKernel(tmp)
        calls = []
        agent.delivery.execute = lambda action, command: calls.append((action, command)) or {
            "status": "completed", "action": action, "deployment_id": "dep-1", "completed": 1
        }

        trace = agent.execute_command("انشر على Railway")

        assert _stage(trace) == "delivery_action"
        assert trace["final"]["accepted"] is True
        assert calls == [("deploy", "انشر على Railway")]


def test_push_and_merge_remain_executive_operations_without_founder_gate():
    with tempfile.TemporaryDirectory() as tmp:
        agent = ExpandedAgentExecutiveKernel(tmp)
        calls = []
        agent.delivery.execute = lambda action, command: calls.append((action, command)) or {
            "status": "completed", "action": action, "commit_sha": "abc123", "completed": 1
        }

        trace = agent.execute_command("ادفع التغييرات إلى GitHub")
        assert _stage(trace) == "delivery_action"
        assert trace["final"]["accepted"] is True
        assert calls == [("push", "ادفع التغييرات إلى GitHub")]
