from __future__ import annotations

from typing import Any, Dict


_COMPLETION_CLAIMS = (
    "تم تنفيذ", "نفذت", "نفّذت", "تم بناء", "بنيت", "تم تعديل", "عدلت", "عدّلت",
    "تم إنشاء", "أنشأت", "انشأت", "أنجزت", "انجزت", "اكتمل التنفيذ", "تم الإنجاز",
    "تم الانجاز", "تم النشر", "نشرت", "نشر بنجاح", "تم الدمج", "دمجت", "تم الدفع",
    "دفعت التغييرات", "صححت الأخطاء", "قمت بتصحيح", "تم تصحيح", "successfully executed",
    "successfully completed", "completed successfully", "deployed successfully", "deployment successful",
)

_VERIFICATION_CLAIMS = (
    "تحققت", "تحقّقت", "تأكدت", "تأكّدت", "راجعت الريلواي", "راجعت railway",
    "راجعت السجلات", "فحصت السجلات", "تحققت من حالة", "تأكدت من حالة",
    "كل شيء يعمل بشكل صحيح", "لا توجد مشاكل", "الأداء مستقر", "verified", "checked the deployment",
)

_PROMISE_CLAIMS = (
    "سأقوم الآن", "سأراجع الآن", "سأتحقق الآن", "سأتحقق", "سأراجع", "سأنفذ", "سأصلح",
    "سأصحح", "سأنشر", "سأدمج", "سأدفع", "سأوافيك", "سأبدأ الآن", "سأعمل على",
    "سأقوم بعملية النشر", "سأقوم بمراجعة", "سأقوم بتنفيذ", "i will deploy", "i'll deploy",
    "i will check", "i'll check", "i will review", "i'll review",
)

_CAPABILITY_CLAIMS = (
    "لدي الصلاحية الكاملة", "عندي الصلاحية الكاملة", "لدي صلاحية", "عندي صلاحية",
    "يمكنني الوصول إلى الريلواي", "أستطيع الوصول إلى الريلواي", "يمكنني النشر على الريلواي",
    "أستطيع النشر على الريلواي", "لدي وصول إلى railway", "full access to railway",
    "i have permission", "i have full access", "i can deploy to railway",
)

_REAL_ACTION_STAGES = {"agent_action", "delivery_action", "final_approval_execute"}


def _step_name(step: Dict[str, Any]) -> str:
    return str(step.get("name") or step.get("stage") or "").strip()


def _walk_dicts(value: Any):
    if isinstance(value, dict):
        yield value
        for item in value.values():
            yield from _walk_dicts(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_dicts(item)


def extract_execution_evidence(trace: Dict[str, Any] | None) -> Dict[str, Any]:
    """Return conservative evidence that a real side effect happened.

    Planning, fluent model output, intent detection, or a claimed future action are
    never proof. File work needs written files/completed units. Delivery/agent work
    needs a completed executable stage plus concrete operation evidence when the
    final payload provides it.
    """
    safe = trace if isinstance(trace, dict) else {}
    pipeline = safe.get("pipeline") or []
    if not isinstance(pipeline, list):
        pipeline = []

    files: list[str] = []
    completed_units = 0
    stages: list[str] = []

    for raw in pipeline:
        if not isinstance(raw, dict):
            continue
        name = _step_name(raw)
        if name:
            stages.append(name)
        output = raw.get("output") or {}
        if not isinstance(output, dict):
            output = {}
        if "FileExecutor" in name:
            try:
                completed_units += max(0, int(output.get("completed") or 0))
            except (TypeError, ValueError):
                pass
            raw_files = output.get("files") or []
            if isinstance(raw_files, list):
                files.extend(str(item) for item in raw_files if str(item).strip())

    final = safe.get("final") or {}
    if not isinstance(final, dict):
        final = {}
    try:
        final_completed = max(0, int(final.get("completed") or 0))
    except (TypeError, ValueError):
        final_completed = 0

    operation_ids: list[str] = []
    operation_statuses: list[str] = []
    capabilities: list[str] = []
    for obj in _walk_dicts(final):
        for key in ("deployment_id", "commit_sha", "pull_request", "job_id", "request_id"):
            value = obj.get(key)
            if value not in (None, ""):
                operation_ids.append(f"{key}:{value}")
        status = obj.get("status")
        if status not in (None, ""):
            operation_statuses.append(str(status))
        capability = obj.get("capability") or obj.get("action")
        if capability not in (None, ""):
            capabilities.append(str(capability))

    normalized_stages = {stage.strip().lower() for stage in stages}
    executable_stage = bool(normalized_stages & _REAL_ACTION_STAGES)
    file_action = bool(files) or completed_units > 0
    real_non_file_action = executable_stage and final_completed > 0 and bool(operation_ids or operation_statuses)
    verified = file_action or real_non_file_action

    unique_files = list(dict.fromkeys(files))
    return {
        "verified": verified,
        "files": unique_files,
        "file_count": len(unique_files),
        "completed_units": completed_units,
        "final_completed": final_completed,
        "stages": stages,
        "operation_ids": list(dict.fromkeys(operation_ids)),
        "operation_statuses": list(dict.fromkeys(operation_statuses)),
        "capabilities": list(dict.fromkeys(capabilities)),
        "kind": "file_execution" if file_action else ("external_operation" if real_non_file_action else "none"),
    }


def _contains(text: str, markers: tuple[str, ...]) -> bool:
    value = (text or "").strip().lower()
    return any(marker.lower() in value for marker in markers)


def claims_execution(text: str) -> bool:
    return _contains(text, _COMPLETION_CLAIMS)


def claims_verification(text: str) -> bool:
    return _contains(text, _VERIFICATION_CLAIMS)


def promises_execution(text: str) -> bool:
    return _contains(text, _PROMISE_CLAIMS)


def claims_capability(text: str) -> bool:
    return _contains(text, _CAPABILITY_CLAIMS)


def enforce_evidence_on_reply(reply: str, evidence: Dict[str, Any]) -> str:
    text = (reply or "").strip()
    verified = bool(evidence.get("verified"))

    if verified:
        file_count = int(evidence.get("file_count") or 0)
        completed = int(evidence.get("completed_units") or evidence.get("final_completed") or 0)
        proof = f"✅ تنفيذ موثق: {completed} خطوة فعلية"
        if file_count:
            proof += f"، {file_count} ملف متغيّر"
        operation_ids = list(evidence.get("operation_ids") or [])
        statuses = list(evidence.get("operation_statuses") or [])
        if operation_ids:
            proof += "، مرجع عملية: " + ", ".join(operation_ids[:3])
        if statuses:
            proof += "، الحالة: " + ", ".join(statuses[:3])
        if proof not in text:
            text = (text + "\n\n" + proof).strip()
        return text

    if claims_execution(text) or claims_verification(text):
        return (
            "⚠️ لا يوجد دليل تنفيذي قابل للتحقق يدعم هذا الادعاء. "
            "لم أسجل تغيير ملفات أو عملية خارجية مكتملة أو نتيجة فحص فعلية، "
            "لذلك لا يجوز لي القول إن التنفيذ/النشر/التحقق تم."
        )

    if promises_execution(text):
        return (
            "⚠️ لم تبدأ عملية تنفيذ فعلية لهذا الإجراء بعد. "
            "لن أقول «سأقوم الآن» إلا بعد إنشاء Job/Tool call حقيقي يمكن تتبعه."
        )

    if claims_capability(text):
        return (
            "⚠️ لا أستطيع تأكيد هذه الصلاحية من الرد المحادثي وحده. "
            "يجب إثبات أن الـcapability مفعلة وأن بيانات الاعتماد/الاتصال متاحة في الـruntime قبل ادعاء الوصول أو النشر."
        )

    return text
