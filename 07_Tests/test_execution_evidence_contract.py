from kernel.execution_evidence import (
    claims_execution,
    enforce_evidence_on_reply,
    extract_execution_evidence,
)


def test_planning_is_not_execution_evidence():
    trace = {
        "pipeline": [
            {"name": "TaskDecomposer", "status": "completed", "output": {"task_count": 3}},
            {"name": "PlanValidator", "status": "passed", "output": {}},
            {"name": "Scheduler", "status": "completed", "output": {"scheduled": 3}},
        ],
        "final": {"accepted": True, "completed": 0},
    }
    evidence = extract_execution_evidence(trace)
    assert evidence["verified"] is False


def test_file_executor_is_real_execution_evidence():
    trace = {
        "pipeline": [
            {
                "name": "FileExecutor",
                "status": "completed",
                "output": {"completed": 2, "files": ["09_Assets/web/index.html", "09_Assets/web/app.js"]},
            }
        ],
        "final": {"accepted": True, "completed": 2},
    }
    evidence = extract_execution_evidence(trace)
    assert evidence["verified"] is True
    assert evidence["file_count"] == 2
    assert evidence["completed_units"] == 2


def test_false_completion_claim_is_replaced():
    evidence = {"verified": False}
    reply = enforce_evidence_on_reply("تم تنفيذ الواجهة بالكامل بنجاح", evidence)
    assert "لم يُسجَّل تنفيذ فعلي" in reply
    assert claims_execution("تم تنفيذ الواجهة") is True


def test_verified_completion_gets_proof_badge():
    evidence = {"verified": True, "file_count": 3, "completed_units": 3, "final_completed": 3}
    reply = enforce_evidence_on_reply("تم تنفيذ الواجهة", evidence)
    assert "تنفيذ موثق" in reply
    assert "3 ملف" in reply
