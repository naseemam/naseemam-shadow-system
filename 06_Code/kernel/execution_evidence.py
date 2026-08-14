from __future__ import annotations

from typing import Any, Dict, Iterable


_COMPLETION_CLAIMS = (
    "تم تنفيذ",
    "نفذت",
    "نفّذت",
    "تم بناء",
    "بنيت",
    "تم تعديل",
    "عدلت",
    "عدّلت",
    "تم إنشاء",
    "أنشأت",
    "انشأت",
    "أنجزت",
    "انجزت",
    "اكتمل التنفيذ",
    "تم الإنجاز",
    "تم الانجاز",
    "successfully executed",
    "successfully completed",
    "completed successfully",
)

_REAL_ACTION_STAGES = {
    "agent_action",
    "delivery_action",
    "final_approval_execute",
}


def _step_name(step: Dict[str, Any]) -> str:
    return str(step.get("name") or step.get("stage") or "").strip()


def extract_execution_evidence(trace: Dict[str, Any] | None) -> Dict[str, Any]:
    """Return conservative evidence that a real side effect happened.

    Planning, validation, scheduling, or a fluent model reply are *not* evidence.
    File execution requires a positive completed count or concrete written files.
    Agent/delivery operations require the final result to report completion.
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

    normalized_stages = {stage.strip().lower() for stage in stages}
    real_non_file_action = bool(normalized_stages & _REAL_ACTION_STAGES) and final_completed > 0
    file_action = bool(files) or completed_units > 0
    verified = file_action or real_non_file_action

    # Stable de-duplication while preserving order.
    unique_files = list(dict.fromkeys(files))
    return {
        "verified": verified,
        "files": unique_files,
        "file_count": len(unique_files),
        "completed_units": completed_units,
        "final_completed": final_completed,
        "stages": stages,
        "kind": "file_execution" if file_action else ("agent_action" if real_non_file_action else "none"),
    }


def claims_execution(text: str) -> bool:
    value = (text or "").strip().lower()
    return any(marker.lower() in value for marker in _COMPLETION_CLAIMS)


def enforce_evidence_on_reply(reply: str, evidence: Dict[str, Any]) -> str:
    text = (reply or "").strip()
    if evidence.get("verified"):
        file_count = int(evidence.get("file_count") or 0)
        completed = int(evidence.get("completed_units") or evidence.get("final_completed") or 0)
        proof = f"✅ تنفيذ موثق: {completed} خطوة فعلية"
        if file_count:
            proof += f"، {file_count} ملف متغيّر"
        if proof not in text:
            text = (text + "\n\n" + proof).strip()
        return text

    if claims_execution(text):
        return (
            "⚠️ لم يُسجَّل تنفيذ فعلي قابل للتحقق لهذا الطلب. "
            "النتيجة الحالية محادثة/تخطيط فقط، ولم يثبت أن ملفًا أو إجراءً حقيقيًا تغيّر."
        )
    return text
