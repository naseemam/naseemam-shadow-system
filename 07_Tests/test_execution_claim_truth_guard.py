from kernel.execution_evidence import enforce_evidence_on_reply


def no_evidence():
    return {
        "verified": False,
        "kind": "none",
        "file_count": 0,
        "completed_units": 0,
        "final_completed": 0,
        "operation_ids": [],
        "operation_statuses": [],
    }


def test_blocks_fake_railway_success_claim():
    text = "تمت عملية النشر بنجاح على الريلواي وتحققت من حالة التطبيق."
    result = enforce_evidence_on_reply(text, no_evidence())
    assert "لم يثبت هذا الادعاء الخارجي" in result


def test_blocks_future_work_promise_without_job():
    text = "سأقوم الآن بمراجعة الريلواي وسأوافيك بالتفاصيل."
    result = enforce_evidence_on_reply(text, no_evidence())
    assert "لم تبدأ عملية تنفيذ فعلية" in result


def test_blocks_broad_capability_claim_without_runtime_proof():
    text = "لدي الصلاحية الكاملة للوصول إلى الريلواي وتعديله والنشر عليه."
    result = enforce_evidence_on_reply(text, no_evidence())
    assert "لا أستطيع تأكيد هذه الصلاحية" in result


def test_file_change_does_not_prove_railway_deployment():
    evidence = {
        "verified": True,
        "kind": "file_execution",
        "file_count": 2,
        "completed_units": 2,
        "final_completed": 0,
        "operation_ids": [],
        "operation_statuses": [],
    }
    text = "تم النشر على الريلواي بنجاح."
    result = enforce_evidence_on_reply(text, evidence)
    assert "لم يثبت هذا الادعاء الخارجي" in result


def test_external_operation_reference_allows_specific_delivery_claim():
    evidence = {
        "verified": True,
        "kind": "external_operation",
        "file_count": 0,
        "completed_units": 0,
        "final_completed": 1,
        "operation_ids": ["deployment_id:dep_123"],
        "operation_statuses": ["SUCCESS"],
    }
    text = "تم النشر على الريلواي بنجاح."
    result = enforce_evidence_on_reply(text, evidence)
    assert text in result
    assert "deployment_id:dep_123" in result


def test_external_success_does_not_prove_full_provider_access():
    evidence = {
        "verified": True,
        "kind": "external_operation",
        "file_count": 0,
        "completed_units": 0,
        "final_completed": 1,
        "operation_ids": ["deployment_id:dep_123"],
        "operation_statuses": ["SUCCESS"],
    }
    text = "لدي الصلاحية الكاملة على الريلواي."
    result = enforce_evidence_on_reply(text, evidence)
    assert "لا يثبت صلاحية كاملة" in result
