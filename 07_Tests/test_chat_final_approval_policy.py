import tempfile
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "06_Code"))

from kernel.expanded_agent import ExpandedAgentExecutiveKernel
from kernel.task_decomposer import TaskDecomposer


def _stage(trace):
    return trace["pipeline"][0]["stage"]


def _result_data(trace):
    return trace["final"]["results"][0]["data"]


def test_design_website_phrase_is_internal_execution_intent():
    result = TaskDecomposer(ROOT).decompose("صمم موقعاً حديثاً للمركز")
    assert result["intent"] == "build_website"
    assert result["task_count"] == 3
    assert result["requires_approval"] is False


def test_delete_requires_chat_final_approval_then_deletes_exact_saved_file():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        target = root / "09_Assets" / "web" / "removable.txt"
        target.parent.mkdir(parents=True)
        target.write_text("delete me", encoding="utf-8")
        agent = ExpandedAgentExecutiveKernel(root)

        pending = agent.execute_command("احذف ملف 09_Assets/web/removable.txt")
        assert _stage(pending) == "final_approval"
        approval = _result_data(pending)["approval"]
        assert target.exists()

        completed = agent.resolve_chat_approval(approval["approval_id"], decision="approve")
        assert _stage(completed) == "final_approval_execute"
        assert completed["final"]["accepted"] is True
        assert not target.exists()


def test_deploy_requires_chat_final_approval_and_replays_saved_command():
    with tempfile.TemporaryDirectory() as tmp:
        agent = ExpandedAgentExecutiveKernel(tmp)
        calls = []
        agent.delivery.execute = lambda action, command: calls.append((action, command)) or {
            "status": "completed", "action": action, "deployment_id": "dep-1", "completed": 1
        }

        pending = agent.execute_command("انشر على Railway")
        assert _stage(pending) == "final_approval"
        approval = _result_data(pending)["approval"]
        assert calls == []

        completed = agent.resolve_chat_approval(approval["approval_id"], decision="approve")
        assert _stage(completed) == "final_approval_execute"
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
