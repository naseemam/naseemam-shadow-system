import ameer_identity_bootstrap as bootstrap


def test_completion_claim_requires_execution_evidence():
    assert bootstrap._claims_completion("تم تنفيذ التعديلات بنجاح") is True
    assert bootstrap._has_execution_evidence({"reply": "تم تنفيذ التعديلات بنجاح"}) is False


def test_completed_file_execution_counts_as_evidence():
    body = {
        "execution_trace": {
            "pipeline": [
                {
                    "name": "FileExecutor",
                    "status": "completed",
                    "output": {"completed": 2, "files": ["09_Assets/web/index.html"]},
                }
            ],
            "final": {"accepted": True, "completed": 2, "files_created": ["09_Assets/web/index.html"]},
        }
    }
    assert bootstrap._has_execution_evidence(body) is True


def test_final_approval_message_is_not_a_completion_claim():
    assert bootstrap._claims_completion("وصلت للبوابة النهائية وأحتاج موافقتك على النشر") is False
