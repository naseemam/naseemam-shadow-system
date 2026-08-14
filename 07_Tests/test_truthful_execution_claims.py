from kernel.execution_evidence import claims_execution, extract_execution_evidence


def test_completion_claim_requires_execution_evidence():
    assert claims_execution("تم تنفيذ التعديلات بنجاح") is True
    assert extract_execution_evidence({})["verified"] is False


def test_completed_file_execution_counts_as_evidence():
    trace = {
        "pipeline": [
            {
                "name": "FileExecutor",
                "status": "completed",
                "output": {"completed": 2, "files": ["09_Assets/web/index.html"]},
            }
        ],
        "final": {"accepted": True, "completed": 2, "files_created": ["09_Assets/web/index.html"]},
    }
    assert extract_execution_evidence(trace)["verified"] is True


def test_final_approval_message_is_not_a_completion_claim():
    assert claims_execution("وصلت للبوابة النهائية وأحتاج موافقتك على النشر") is False
