"""Provider/model adapters for Ameer workers.

Credentials are read only from runtime environment variables and never persisted
in the worker registry or repository. The adapter returns model output as evidence;
file edits, external calls, deployment, and irreversible actions still pass through
Ameer's execution boundary and the founder approval gate.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Dict

from kernel.worker_runtime import WorkerRuntimeRegistry


DEFAULT_MODELS = {
    "engineering": "gpt-5",
    "design": "gpt-5",
    "research": "gpt-5-mini",
    "communications": "gpt-5-mini",
    "operations": "gpt-5-mini",
    "business": "gpt-5-mini",
    "school": "gpt-5-mini",
    "store": "gpt-5-mini",
}

ROLE_PROMPTS = {
    "engineering": "أنت عامل هندسة تحت إدارة أمير. حلل المهمة تقنيًا، اقترح تغييرات قابلة للتنفيذ، ولا تنفذ نشرًا أو دمجًا أو حذفًا.",
    "design": "أنت عامل تصميم UI/UX تحت إدارة أمير. حلل الواجهة، اقترح تحسينات قابلة للتنفيذ، واذكر الملفات والمكونات المتأثرة دون ادعاء تعديل لم يحدث.",
    "research": "أنت عامل بحث وتحليل تحت إدارة أمير. قدم نتائج منظمة مع تمييز الحقائق عن الاستنتاجات.",
    "communications": "أنت عامل اتصالات تحت إدارة أمير. جهز قراءة أو مسودة، ولا ترسل أي رسالة دون موافقة نهائية.",
    "operations": "أنت عامل عمليات تحت إدارة أمير. حلل الحالة وسجل الإجراءات، ولا تنفذ أثرًا خارجيًا دون موافقة.",
    "business": "أنت عامل أعمال تحت إدارة أمير. حلل بيانات الأعمال واقترح إجراءات، ولا تنفذ تغييرات مؤثرة دون موافقة.",
    "school": "أنت عامل سجلات تحت إدارة أمير. نظم المعلومات وقدم متابعة دقيقة، ولا تعدل سجلات حساسة دون موافقة.",
    "store": "أنت Store Agent لمركز حلم الندى تحت إدارة أمير. تخصصك إدارة المخزون والموظفين والحجوزات والطلبات والتقارير. اعمل داخل نطاق المركز فقط، وقدّم خطة ونتيجة قابلة للتدقيق، ولا تنفذ حذفًا أو إرسالًا أو تعديلًا خارجيًا أو تغييرًا حساسًا دون موافقة أمير ثم الموافقة النهائية للمؤسس.",
}


def _api_base() -> str:
    """Return a normalized OpenAI-compatible base URL without endpoint suffixes."""
    raw = (os.getenv("AMEER_LLM_API_BASE") or os.getenv("OPENAI_API_BASE") or "").strip()
    if not raw:
        return ""
    if "://" not in raw:
        raw = f"https://{raw}"
    raw = raw.rstrip("/")
    if raw.endswith("/v1/chat/completions"):
        raw = raw[: -len("/chat/completions")].rstrip("/")
    elif raw.endswith("/chat/completions"):
        raw = raw[: -len("/chat/completions")].rstrip("/")
    return raw


def _api_key() -> str:
    return os.getenv("AMEER_LLM_API_KEY") or os.getenv("OPENAI_API_KEY") or ""


def _call_chat(model: str, system: str, objective: str, context: Dict[str, Any]) -> Dict[str, Any]:
    base = _api_base()
    key = _api_key()
    if not base or not key:
        raise RuntimeError("llm_credentials_unavailable")
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps({"objective": objective, "context": context}, ensure_ascii=False)},
        ],
    }
    request = urllib.request.Request(
        f"{base}/chat/completions",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"llm_http_{exc.code}:{detail}") from exc
    choices = body.get("choices") or []
    content = ((choices[0].get("message") or {}).get("content") if choices else "") or ""
    return {"status": "completed", "model": model, "content": content, "usage": body.get("usage", {})}


def configure_workers_from_env(registry: WorkerRuntimeRegistry) -> Dict[str, Any]:
    """Bind all worker roles to the configured provider/model when credentials exist."""
    configured = bool(_api_base() and _api_key())
    result = {"provider": "openai_compatible", "configured": configured, "workers": {}}
    for worker_id, default_model in DEFAULT_MODELS.items():
        model = os.getenv(f"AMEER_WORKER_{worker_id.upper()}_MODEL", default_model)
        if configured:
            registry.register_runtime(
                worker_id,
                provider="openai_compatible",
                model=model,
                adapter="chat_completions",
                status="ready",
            )
            registry.register_handler(
                worker_id,
                lambda objective, context, worker_id=worker_id, model=model: _call_chat(
                    model, ROLE_PROMPTS[worker_id], objective, context
                ),
            )
        else:
            registry.register_runtime(
                worker_id,
                provider="openai_compatible",
                model=model,
                adapter="chat_completions",
                status="configured",
            )
        result["workers"][worker_id] = registry.get(worker_id)
    return result
