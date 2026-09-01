from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import glob
import json
import html
import logging
import os
import re
import tempfile
import sys
import uuid
import importlib.util
from pathlib import Path
from datetime import datetime, timezone

# ─── 06_Code on sys.path — must be first so kernel imports resolve everywhere ─
_CODE_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "06_Code")
if _CODE_ROOT not in sys.path:
    sys.path.insert(0, _CODE_ROOT)

from kernel.task_decomposer import normalize_arabic_for_match
from kernel.ameer_authority import policy_snapshot as authority_policy_snapshot
from kernel.chat_media import ChatMediaStore, MAX_UPLOAD_BYTES

from ameer_runtime import (
    public_runtime_identity,
    print_runtime_banner,
    resolve_data_root,
    resolve_host,
    resolve_port,
    runtime_headers,
    runtime_metadata,
)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# ─── Structured logger ────────────────────────────────────────────────────────

_log_handler = logging.StreamHandler(sys.stdout)
_log_handler.setFormatter(logging.Formatter("%(message)s"))
_logger = logging.getLogger("ameer")
_logger.setLevel(logging.INFO)
_logger.propagate = False
if not _logger.handlers:
    _logger.addHandler(_log_handler)


def _log(event: str, level: str = "info", request_id: str | None = None, **kwargs) -> None:
    record = {
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "level": level,
        "event": event,
    }
    if request_id:
        record["request_id"] = request_id
    record.update(kwargs)
    # Sanitize before writing to logs so credentials never appear in log output.
    safe_record = _sanitize_log_record(record)
    getattr(_logger, level, _logger.info)(json.dumps(safe_record, ensure_ascii=False))


def _sanitize_log_record(record: dict) -> dict:
    """Apply credential sanitization to a log record.

    Imported lazily to avoid circular-import issues during module load; the
    sanitizer module lives inside 06_Code which is added to sys.path below.
    """
    try:
        from kernel.credential_sanitizer import sanitize as _cs
        return _cs(record)
    except Exception:
        return record


def load_orchestrator_class():
    module_path = os.path.join(os.path.dirname(__file__), "06_Code", "reasoning_orchestrator.py")
    spec = importlib.util.spec_from_file_location("reasoning_orchestrator", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load reasoning_orchestrator module")
    module = importlib.util.module_from_spec(spec)
    sys.modules["reasoning_orchestrator"] = module
    spec.loader.exec_module(module)
    return module.AmeerOrchestrator


def load_executive_brain():
    module_path = os.path.join(os.path.dirname(__file__), "06_Code", "executive_brain.py")
    spec = importlib.util.spec_from_file_location("executive_brain", module_path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    # Must register in sys.modules BEFORE exec so @dataclass can resolve __module__
    sys.modules["executive_brain"] = module
    spec.loader.exec_module(module)
    return module.ExecutiveBrain


def load_response_formatter():
    module_path = os.path.join(os.path.dirname(__file__), "06_Code", "response_formatter.py")
    spec = importlib.util.spec_from_file_location("response_formatter", module_path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    sys.modules["response_formatter"] = module
    spec.loader.exec_module(module)
    return module.ResponseFormatter


def load_executive_conversation():
    module_path = os.path.join(os.path.dirname(__file__), "06_Code", "executive_conversation.py")
    spec = importlib.util.spec_from_file_location("executive_conversation", module_path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    sys.modules["executive_conversation"] = module
    spec.loader.exec_module(module)
    return module.ExecutiveConversationEngine


AmeerOrchestrator = load_orchestrator_class()
ExecutiveBrainClass = load_executive_brain()
ResponseFormatterClass = load_response_formatter()
ExecutiveConversationEngineClass = load_executive_conversation()

app = FastAPI(title="Ameer Local Server")


# REPO_ROOT: repository checkout directory — used for static assets and documents.
# DATA_ROOT: parent of the .ameer state directory — may be redirected to a
#            persistent volume via AMEER_DATA_DIR (see ameer_runtime.resolve_data_root).
REPO_ROOT = os.path.dirname(__file__)
DATA_ROOT = str(resolve_data_root())
CHAT_MEDIA = ChatMediaStore(DATA_ROOT)

# Load markdown documents from workspace (always from the repo checkout)
ROOT = DATA_ROOT
MODULES_DIR = os.path.join(REPO_ROOT, "09_Assets", "web", "modules")
app.mount("/modules", StaticFiles(directory=MODULES_DIR), name="modules")
MD_GLOB = os.path.join(REPO_ROOT, "**", "*.md")
WEB_INDEX = os.path.join(REPO_ROOT, "09_Assets", "web", "index.html")
DEBUG_MODE = os.getenv("AMEER_DEBUG", "0").lower() in {"1", "true", "yes", "on"}
RUNTIME_METADATA = runtime_metadata(workspace_root=REPO_ROOT)
KERNEL_ACTIONABLE_INTENTS = {
    "build_homepage", "build_generic", "file_read", "run_test",
    "repository_review", "code_edit", "build_website", "build_store",
    "open_branch", "open_pull_request", "deploy_railway", "worker_dispatch",
}

_WORKER_REQUEST_MARKERS = {
    "engineering": ("عامل الهندسة", "عامل هندسة", "مهندس", "engineering worker"),
    "design": ("عامل التصميم", "عامل تصميم", "المصمم", "design worker", "ui ux"),
    "business": ("عامل الأعمال", "عامل اعمال", "عامل الأعمال", "business worker"),
    "school": ("عامل المدرسة", "عامل مدرس", "school worker"),
    "research": ("عامل البحث", "عامل بحث", "research worker"),
    "communications": ("عامل الاتصالات", "عامل تواصل", "communications worker"),
    "operations": ("عامل العمليات", "عامل عمليات", "operations worker"),
    "store": ("عامل المتجر", "عامل حلم الندى", "store worker"),
    "specialist": ("عامل متخصص", "عامل التخصص", "specialist worker"),
}


def _requested_worker_id(query: str) -> str:
    """Return an explicitly requested worker, never infer one from casual text."""
    text = normalize_arabic_for_match(query or "")
    if not any(token in text for token in ("عامل", "worker", "استدع", "شغل", "اختبر")):
        return ""
    for worker_id, markers in _WORKER_REQUEST_MARKERS.items():
        if any(normalize_arabic_for_match(marker) in text for marker in markers):
            return worker_id
    return ""


_WORKER_AUTO_ROUTE_RULES = (
    ("store", ("حلم الندى", "المخزون", "الحجوزات", "الموظفين", "المتجر", "الطلبات")),
    ("school", ("المدرسة", "الطلاب", "الحضور", "الدرجات", "الواجبات")),
    ("communications", ("بريد", "ايميل", "إيميل", "رسالة", "موعد", "تقويم")),
    ("research", ("ابحث", "بحث", "دراسة", "مقارنة", "مصادر", "تقرير")),
    ("business", ("العملاء", "عميل", "المبيعات", "الصفقات", "حجوزات العملاء")),
    ("design", ("واجهة", "ui", "ux", "تصميم", "تجربة المستخدم", "هوية بصرية")),
    ("engineering", ("كود", "برمجة", "خطأ", "bug", "api", "اختبار", "python", "javascript", "css", "html")),
)
_WORKER_ACTION_MARKERS = (
    "راجع", "حلل", "افحص", "صمم", "رتب", "نظم", "ابحث", "جهز",
    "review", "analyze", "design", "research", "prepare",
)
_DIRECT_KERNEL_ACTION_MARKERS = (
    "أنشئ", "انشئ", "ابن", "عدل", "اصلح", "صلح", "اكتب", "اختبر", "شغل الاختبارات",
    "انشر", "ادمج", "صمم موقع", "صمم الموقع",
    "create", "build", "edit", "fix", "run test", "deploy", "merge", "design website",
)


def _select_worker_id(query: str) -> tuple[str, str]:
    """Choose a worker for an actionable specialist task; never route greetings or vague chat."""
    explicit = _requested_worker_id(query)
    if explicit:
        return explicit, "explicit"
    text = normalize_arabic_for_match(query or "")
    if not text or not any(marker in text for marker in _WORKER_ACTION_MARKERS):
        return "", ""
    # Build, write, test, merge, and publish requests retain their governed
    # kernel path; a worker must not silently replace the real operation.
    if any(normalize_arabic_for_match(marker) in text for marker in _DIRECT_KERNEL_ACTION_MARKERS):
        return "", ""
    for worker_id, markers in _WORKER_AUTO_ROUTE_RULES:
        if any(normalize_arabic_for_match(marker) in text for marker in markers):
            return worker_id, "automatic"
    # No existing role covers the request: use the constrained on-demand
    # specialist instead of inventing a capability or returning a vague reply.
    return "specialist", "automatic"


def _worker_result_content(worker_result: dict) -> str:
    result = worker_result.get("result") if isinstance(worker_result.get("result"), dict) else worker_result
    content = str(result.get("content") or "").strip()
    return str(_sanitize_response_payload(content))[:1800]


# ─── Executive Operating Kernel ───────────────────────────────────────────────

def _load_executive_kernel():
    try:
        kernel_path = os.path.join(os.path.dirname(__file__), "06_Code", "kernel", "executive_kernel.py")
        spec = importlib.util.spec_from_file_location("executive_kernel", kernel_path)
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        sys.modules["executive_kernel"] = module
        spec.loader.exec_module(module)
        return module.ExecutiveKernel
    except Exception:
        return None


_ExecutiveKernelClass = _load_executive_kernel()
KERNEL = _ExecutiveKernelClass(workspace_root=ROOT) if _ExecutiveKernelClass else None
EXECUTIVE_CONVERSATION_ENGINE = (
    ExecutiveConversationEngineClass(workspace_root=ROOT) if ExecutiveConversationEngineClass else None
)

# ─── Execution Boundary (central gate for all side-effecting execution) ────────

def _load_execution_boundary():
    try:
        from kernel.execution_boundary import ExecutionBoundary
        approval_gate = KERNEL.approvals if KERNEL else None
        execution_auth = KERNEL.execution_auth if KERNEL else None
        return ExecutionBoundary(approval_gate=approval_gate, execution_auth=execution_auth)
    except Exception:
        return None


EXECUTION_BOUNDARY = _load_execution_boundary()

try:
    from kernel.agent_message_bus import AgentMessageBus
    from kernel.worker_runtime import DEFAULT_WORKERS
    from kernel.business_operations import BusinessOperations
    from kernel.school_operations import SchoolOperations, SCHOOL_TASK_CATEGORIES
    from kernel.commerce_test_environment import CommerceTestEnvironment
    from kernel.tap_webhook_verifier import verify_tap_hashstring, tap_status_to_test_status
    MESSAGE_BUS = AgentMessageBus(ROOT)
    BUSINESS_OPERATIONS = BusinessOperations(ROOT)
    SCHOOL_OPERATIONS = SchoolOperations(ROOT)
    COMMERCE_TEST = CommerceTestEnvironment(ROOT)
except Exception:
    AgentMessageBus = None
    DEFAULT_WORKERS = {}
    MESSAGE_BUS = None
    BUSINESS_OPERATIONS = None
    SCHOOL_OPERATIONS = None
    SCHOOL_TASK_CATEGORIES = {}
    COMMERCE_TEST = None
    verify_tap_hashstring = None
    tap_status_to_test_status = None


def load_documents():
    # Paths (relative to ROOT) that must be excluded from the knowledge corpus.
    # Backups may contain outdated or conflicting information; root junk files are not
    # official documents.
    _EXCLUDED_PREFIXES = (
        "08_Backups/",
        "08_DevTools/",
        "__pycache__/",
    )
    _EXCLUDED_ROOT_FILES = {
        "hello.txt",
        "test_from_browser.txt",
        "meeting.md",
        "demo_notes.md",
    }
    docs = []
    for path in glob.glob(MD_GLOB, recursive=True):
        try:
            rel = os.path.relpath(path, REPO_ROOT).replace("\\", "/")
            # Skip excluded prefixes
            if any(rel.startswith(prefix) for prefix in _EXCLUDED_PREFIXES):
                continue
            # Skip root-level junk files
            if rel in _EXCLUDED_ROOT_FILES:
                continue
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()
            docs.append({"path": rel, "text": text})
        except Exception:
            continue
    return docs


def refresh_documents():
    global DOCUMENTS
    DOCUMENTS = load_documents()
    return DOCUMENTS


def _sanitize_response_payload(value):
    # First remove internal debug fields (traceback, stack)
    if isinstance(value, dict):
        clean = {}
        for k, v in value.items():
            key = str(k).lower()
            if "traceback" in key or "stack" in key:
                continue
            clean[k] = _sanitize_response_payload(v)
        value = clean
    elif isinstance(value, list):
        value = [_sanitize_response_payload(v) for v in value]
    # Then apply credential sanitization
    try:
        from kernel.credential_sanitizer import sanitize as _cs
        return _cs(value)
    except Exception:
        return value


def utf8_json_response(payload, headers: dict[str, str] | None = None, status_code: int = 200):
    safe_payload = _sanitize_response_payload(payload)
    return JSONResponse(content=safe_payload, headers=headers or {}, status_code=status_code)


DOCUMENTS = load_documents()

class AskRequest(BaseModel):
    query: str | None = None  # Make query optional
    max_results: int = 5
    room: str = "business"
    attachments: list[str] | None = None

    class Config:
        extra = 'allow'


class MemoryRequest(BaseModel):
    text: str
    source: str = "founder"
    target_layer: str = "founder_memory"
    confidence: float = 0.7


class KnowledgePromotionRequest(BaseModel):
    item_id: str
    reason: str
    approved_by: str = "naseem"


class ProjectRequest(BaseModel):
    name: str
    description: str | None = None


class AutonomyPlanRequest(BaseModel):
    query: str
    goal: str | None = None


def normalize_arabic(text: str) -> str:
    # Normalize common Arabic letter variants and remove diacritics/tatweel.
    t = text
    t = re.sub(r"[\u064B-\u065F\u0670]", "", t)
    t = t.replace("ـ", "")
    t = t.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    t = t.replace("ى", "ي")
    t = t.replace("ؤ", "و").replace("ئ", "ي")
    t = t.replace("ة", "ه")
    return t

def score_text(query, text):
    # simple scoring by word overlap
    nq = normalize_arabic(query.lower())
    nt = normalize_arabic(text.lower())
    qwords = re.findall(r"\w+", nq)
    twords = re.findall(r"\w+", nt)
    if not qwords or not twords:
        return 0
    score = 0
    tset = set(twords)
    for w in qwords:
        if w in tset:
            score += 1
    return score


def _boundary_for_server_execution():
    return EXECUTION_BOUNDARY or _load_execution_boundary()


_PROBE_FORBIDDEN_TERMS = (
    "نشر", "ارسل", "أرسل", "إرسال", "حذف", "احذف", "دمج", "ادفع", "دفع", "شراء",
    "send", "deploy", "delete", "merge", "push",
)
_PROBE_NEGATION_TERMS = ("لا", "ما", "لن", "لم", "ليس", "لست", "مش", "دون", "بدون", "من غير", "without", "no")


def _probe_occurrence_is_negated(text: str, start: int) -> bool:
    prefix = text[max(0, start - 40):start].lower()
    tokens = re.findall(r"[\w\u0600-\u06ff]+", prefix)
    return any(token in _PROBE_NEGATION_TERMS for token in tokens[-4:])


def _probe_has_non_negated_forbidden_term(text: str) -> bool:
    lowered = (text or "").lower()
    for term in _PROBE_FORBIDDEN_TERMS:
        pattern = re.escape(term)
        for match in re.finditer(pattern, lowered):
            if not _probe_occurrence_is_negated(lowered, match.start()):
                return True
    return False


def _manage_project_context(query: str) -> dict | None:
    text = (query or "").strip()
    if not text:
        return None

    lowered = text.lower()
    create_markers = [
        "ابن موقع", "أبني موقع", "أنشئ موقع", "انشئ موقع",
        "ابن مشروع", "أبني مشروع", "أنشئ مشروع", "انشئ مشروع",
        "موقع جديد", "مشروع جديد", "create a project", "create a website",
        "build a project", "build a website",
    ]
    continue_markers = ["أكمل المشروع", "اكمل المشروع", "continue project", "continue the project"]

    if any(marker in lowered for marker in create_markers):
        projects = _load_project_store()
        name = "موقع جديد"
        if "مشروع" in lowered or "project" in lowered:
            name = "مشروع جديد"
        if "موقع" in lowered or "website" in lowered:
            name = "موقع جديد"
        existing = [p for p in projects if p.get("name", "").lower() == name.lower()]
        if not existing:
            projects.append({"name": name, "description": text, "created_at": datetime.now(timezone.utc).isoformat()})
            _save_project_store(projects)
        return {"mode": "created", "project": name}

    if any(marker in lowered for marker in continue_markers):
        projects = _load_project_store()
        if projects:
            latest = projects[-1]
            return {"mode": "continued", "project": latest.get("name", "المشروع")}

    return None


ORCHESTRATOR = AmeerOrchestrator(
    documents=DOCUMENTS,
    score_fn=score_text,
    normalize_fn=normalize_arabic,
)

EXECUTIVE_BRAIN = ExecutiveBrainClass(normalize_fn=normalize_arabic) if ExecutiveBrainClass else None
RESPONSE_FORMATTER = ResponseFormatterClass() if ResponseFormatterClass else None

FRIENDLY_EXECUTION_MARKERS = (
    "نفذ", "تنفيذ", "اكتب", "اكتب لي", "أنشئ", "انشئ", "حسن", "حسّن", "طور", "طوّر", "صمم", "صمّم", "انشر", "أرسل", "احذف", "عدّل", "عدل", "برمج", "ابنِ", "ابني"
)
FRIENDLY_BUSINESS_MARKERS = (
    "المخزون", "الموظف", "الموظفين", "العملاء", "الحجوزات", "الحجز", "المتجر", "الطلب", "مركز حلم الندى", "store agent"
)


def _friendly_room_blocked(query: str) -> bool:
    text = (query or "").strip().lower()
    return any(marker.lower() in text for marker in FRIENDLY_EXECUTION_MARKERS + FRIENDLY_BUSINESS_MARKERS)


def _friendly_personal_reply(query: str) -> str:
    """Return a direct personal-room reply without invoking executive planning."""
    text = (query or "").strip()
    normalized = text.lower().replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    normalized = " ".join(normalized.replace("؟", " ").replace("!", " ").replace("،", " ").split())
    name_calls = {"امير", "اميري", "يا امير", "يا اميري", "امير يا امير"}
    if normalized in name_calls:
        return "نعم، أنا معك. ماذا تحتاج؟"
    if any(phrase in normalized for phrase in ("ايش تكمل", "وش تكمل", "ماذا تكمل", "انا اناديك", "أنا اناديك")):
        return "معك حق، أنا أستمع لك الآن. ناديتني فقط؛ كيف تحب أن أساعدك أو نتحدث؟"
    if any(phrase in normalized for phrase in ("كيف حالك", "كيفك", "شلونك")):
        return "أنا بخير ما دمت معك. كيف حالك أنت؟"
    if any(phrase in normalized for phrase in ("شكرا", "شكر")):
        return "العفو، أنا معك دائمًا."
    return "أنا معك في المحادثة الودية. تحدث معي براحتك؛ ماذا يدور في بالك؟"


def _execution_result_output(item: dict) -> str:
    """Return a bounded, display-safe evidence snippet from one kernel result."""
    record = item.get("result") if isinstance(item.get("result"), dict) else item
    output = record.get("stdout") or record.get("content") or item.get("stdout") or item.get("content") or ""
    output = str(_sanitize_response_payload(output)).strip()
    return output[:1200]


def _format_kernel_execution_reply(intent: str, final: dict) -> str:
    """Describe the operation actually completed, never a generic homepage claim."""
    results = [item for item in (final.get("results") or []) if isinstance(item, dict)]
    completed = int(final.get("completed") or 0)
    files = [str(path) for path in (final.get("files_created") or []) if path]

    if intent == "repository_review":
        evidence = [snippet for item in results if (snippet := _execution_result_output(item))]
        report = "\n\n".join(evidence)
        prefix = "✅ أجريت مراجعة فعلية للمستودع باستخدام مسار التحليل والقراءة المصرح به."
        if report:
            return f"{prefix}\n\nنتيجة المراجعة:\n{report}"
        return f"{prefix}\n\nلم تُظهر أوامر الحالة والفروق أي مخرجات محلية قابلة للعرض."

    if intent == "run_test":
        evidence = [snippet for item in results if (snippet := _execution_result_output(item))]
        report = "\n\n".join(evidence)
        prefix = f"✅ شغّلت الاختبارات فعلياً عبر صلاحية التنفيذ المحلي المقيدة. اكتملت {completed} مهمة."
        return f"{prefix}\n\n{report}" if report else prefix

    if intent == "code_edit":
        target = files[0] if files else "مساحة العمل المراقبة"
        return f"✅ سجلت طلب تعديل الكود في {target} ضمن صلاحية الكتابة المتتبعة؛ لم يُنشر أي تغيير خارجي."

    if intent in {"build_homepage", "build_generic", "build_website", "build_store"}:
        file_list = "، ".join(files)
        return (
            f"✅ اكتمل بناء العمل المطلوب ضمن مساحة التنفيذ المراقبة. أُنجزت {completed} مهمة"
            + (f": {file_list}." if file_list else ".")
        )

    return f"✅ اكتمل التنفيذ المصرح به للمسار «{intent}» عبر {completed} مهمة موثقة."


@app.post('/friendly-chat')
async def friendly_chat(request: Request):
    """Conversation-only room: no worker dispatch, file work, or external effect."""
    request_id = str(uuid.uuid4())
    try:
        payload = await request.json()
        req = AskRequest(**(payload if isinstance(payload, dict) else {}))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")
    q = req.query.strip() if isinstance(req.query, str) else ""
    if not q:
        raise HTTPException(status_code=400, detail="Empty query")
    if _friendly_room_blocked(q):
        return utf8_json_response({
            "status": "room_switch_required",
            "room": "friendly",
            "message": "هذه الغرفة للمحادثة الودية فقط. افتح غرفة الأعمال إذا أردت طلبًا تنفيذيًا أو متعلقًا بمركز حلم الندى.",
            "execution": {"started": False, "external_effect": False},
            "request_id": request_id,
        }, status_code=200)
    # The personal room intentionally bypasses executive planning, task state,
    # and provider orchestration.  It must answer a personal call as a person,
    # not surface an operational recommendation such as "أكمل على هذا".
    reply = _friendly_personal_reply(q)
    return utf8_json_response({
        "status": "completed", "room": "friendly", "reply": reply, "message": reply,
        "execution": {"started": False, "external_effect": False, "worker_dispatch": False},
        "request_id": request_id,
    })


@app.post("/chat/uploads")
async def upload_business_attachment(
    file: UploadFile = File(...),
    room: str = Form("business"),
):
    """Persist a founder attachment for the existing business-chat asset."""
    if str(room or "business").strip().lower() != "business":
        raise HTTPException(status_code=400, detail="Attachments are available in business chat only")
    try:
        data = await file.read(MAX_UPLOAD_BYTES + 1)
        metadata = CHAT_MEDIA.save(
            filename=file.filename or "attachment",
            content_type=file.content_type or "application/octet-stream",
            data=data,
        )
    except ValueError as exc:
        detail = str(exc)
        status = 413 if detail == "attachment_exceeds_50mb_limit" else 400
        raise HTTPException(status_code=status, detail=detail) from exc
    finally:
        await file.close()

    public = CHAT_MEDIA.public(metadata)
    _log(
        "chat_attachment_uploaded",
        attachment_id=metadata["attachment_id"],
        filename=metadata["filename"],
        category=metadata["category"],
        size_bytes=metadata["size_bytes"],
    )
    return utf8_json_response({"attachment": public}, headers=runtime_headers(workspace_root=REPO_ROOT))


@app.get("/chat/uploads/{attachment_id}")
async def download_business_attachment(attachment_id: str):
    try:
        metadata = CHAT_MEDIA.get(attachment_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="attachment_not_found") from exc
    return FileResponse(
        metadata["path"],
        media_type=metadata["mime_type"],
        filename=metadata["filename"],
    )


@app.post('/ask')
async def ask(request: Request):
    request_id = str(uuid.uuid4())
    raw = await request.body()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty body")

    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=400, detail="Invalid UTF-8 JSON body") from exc

    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Expected JSON object")

    req = AskRequest(**payload)
    q = req.query.strip() if isinstance(req.query, str) else ''
    if not q:
        raise HTTPException(status_code=400, detail="Empty query")

    attachment_ids = [item for item in (req.attachments or []) if isinstance(item, str)][:12]
    try:
        attachment_context, attached_files = CHAT_MEDIA.attachment_context(attachment_ids)
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=400, detail=f"invalid_attachment: {exc}") from exc
    reasoning_query = q + attachment_context

    _log(
        "ask_received",
        request_id=request_id,
        build_id=RUNTIME_METADATA["build_id"],
        attachment_count=len(attached_files),
    )
    if MESSAGE_BUS is not None:
        try:
            MESSAGE_BUS.send(
                sender="user",
                recipient="ameer",
                body=q,
                kind="chat_command",
                metadata={"channel": "web", "request_id": request_id},
            )
        except Exception:
            _log("agent_message_record_failed", level="warning", request_id=request_id)

    # ── 1. Executive Kernel: build full executive context (pipeline step 1→5) ──
    # Pipeline: Kernel → State → Workspace → Founder → Session → Brain
    conversation_context = ""
    founder_context = ""
    workspace_summary = ""
    pending_approvals: list = []
    active_projects: list = []
    running_tasks: list = []
    executive_assessment = ""
    persistent_memory_context = ""
    is_first_turn = False
    if KERNEL:
        try:
            ctx = KERNEL.before_request(q)
            conversation_context = ctx.get("conversation_context", "")
            founder_context = ctx.get("founder_context", "")
            workspace_summary = ctx.get("workspace_summary", "")
            pending_approvals = ctx.get("pending_approvals", [])
            active_projects = ctx.get("active_projects", [])
            running_tasks = ctx.get("running_tasks", [])
            executive_assessment = ctx.get("executive_assessment", "")
            persistent_memory_context = ctx.get("persistent_memory_context", "")
            is_first_turn = ctx.get("is_first_turn", False)
        except Exception:
            pass

    autonomy_plan = None
    autonomy_keywords = ["plan", "planning", "memory", "autonom", "workspace", "document", "tool", "improve", "self", "reason"]
    if any(keyword in q.lower() for keyword in autonomy_keywords):
        autonomy_plan = _record_autonomy_plan(q, "autonomy")

    # ── 2. Orchestrator (retrieval + guardian) ─────────────────────────────────
    orchestrator_result = ORCHESTRATOR.answer(q, req.max_results)

    if not EXECUTIVE_BRAIN:
        raise HTTPException(status_code=500, detail="Executive Brain is unavailable")

    guardian = orchestrator_result.get("guardian", {})
    routing = orchestrator_result.get("routing") or {}
    project_manager = _manage_project_context(q)

    # A specialist task is delegated by Ameer only after routing and governance
    # have both passed.  Explicit selection is honoured; otherwise the routing
    # rules choose a ready domain worker for an actionable task.
    requested_worker, worker_selection_mode = _select_worker_id(q)
    worker_execution_trace: dict | None = None
    worker_execution_reply: str | None = None
    if requested_worker and KERNEL and getattr(KERNEL, "worker_runtime", None):
        if str((guardian or {}).get("status") or "").strip().lower() == "pass":
            worker_context = {
                "mode": "business_chat_worker_dispatch",
                "tools": [],
                "request_id": request_id,
                "room": "business",
                "selection_mode": worker_selection_mode,
                "ameer_review": True,
            }
            if getattr(KERNEL, "orchestrator", None):
                delegation = KERNEL.orchestrator.execute_delegation(
                    requested_worker,
                    q,
                    worker_context,
                )
                worker_result = delegation.get("worker_result") or delegation
                worker_status = str(delegation.get("status") or worker_result.get("status") or "failed")
                worker_delegation_id = delegation.get("correlation_id")
            else:
                worker_result = KERNEL.worker_runtime.dispatch(requested_worker, q, worker_context)
                worker_status = str(worker_result.get("status") or "failed")
                worker_delegation_id = None
            worker_run_id = worker_result.get("run_id")
            worker_execution_trace = {
                "command": q,
                "pipeline": [{
                    "step": 1,
                    "name": "WorkerRuntime",
                    "status": worker_status,
                    "output": worker_result,
                }],
                "final": {
                    "accepted": worker_status == "completed",
                    "intent": "worker_dispatch",
                    "completed": 1 if worker_status == "completed" else 0,
                    "failed": 0 if worker_status == "completed" else 1,
                    "blocked": 0,
                    "run_id": worker_run_id,
                    "worker_id": requested_worker,
                    "delegation_id": worker_delegation_id,
                    "selection_mode": worker_selection_mode,
                    "results": [{
                        "task_id": worker_run_id or f"worker-{requested_worker}",
                        "worker_id": requested_worker,
                        "run_id": worker_run_id,
                        "delegation_id": worker_delegation_id,
                        "status": worker_status,
                        "result": worker_result.get("result"),
                        "reason": worker_result.get("reason"),
                    }],
                },
            }
            selection_text = "تلقائياً" if worker_selection_mode == "automatic" else "بناءً على طلبك"
            if worker_status == "completed":
                evidence = _worker_result_content(worker_result)
                worker_execution_reply = (
                    f"✅ وجّه أمير المهمة {selection_text} إلى عامل {requested_worker}. "
                    f"رقم التشغيل: {worker_run_id or 'مسجل'}"
                    + (f"، ومعرّف التفويض: {worker_delegation_id}." if worker_delegation_id else ".")
                    + (f"\n\nنتيجة العامل:\n{evidence}" if evidence else "")
                )
            else:
                worker_execution_reply = (
                    f"⚠️ اختار أمير عامل {requested_worker} {selection_text}، لكنه لم يكتمل. "
                    f"السبب التقني: {worker_result.get('reason') or worker_result.get('error') or worker_status}."
                )
        else:
            worker_execution_trace = {
                "command": q,
                "pipeline": [],
                "final": {
                    "accepted": False,
                    "intent": "worker_dispatch",
                    "reason": "guardian_not_pass",
                    "technical_reason": "لم يمنح مسار الحوكمة تصريحًا صالحًا لاستدعاء العامل.",
                    "completed": 0,
                    "failed": 0,
                    "blocked": 1,
                    "worker_id": requested_worker,
                    "selection_mode": worker_selection_mode,
                },
            }
            worker_execution_reply = "⚠️ لم يُستدع العامل لأن تصريح الحوكمة الحالي غير صالح."

    # ── 3. Executive Brain think + execute ────────────────────────────────────
    plan = EXECUTIVE_BRAIN.think(
        reasoning_query,
        DOCUMENTS,
        guardian_result=guardian,
        routing_hint=routing,
    )
    # P0.2 — pass existing plan so get_reasoning_output does NOT call think() again
    reasoning_output = EXECUTIVE_BRAIN.get_reasoning_output(
        reasoning_query,
        DOCUMENTS,
        guardian_result=guardian,
        routing_hint=routing,
        existing_plan=plan,
    )
    reasoning_output["_plan"] = plan

    # ── P0.1 — Governance wiring: route plan outcomes into Kernel automatically ──
    # Every high-impact outcome is now recorded in DecisionEngine or ApprovalGate
    # so the governance layer is populated without manual API calls.
    if KERNEL:
        try:
            g_status = getattr(plan, "guardian_status", "pass")
            req_type = getattr(plan, "request_type", "")

            # 1. Needs-approval requests → create an ApprovalGate record
            if g_status == "needs_approval":
                KERNEL.request_approval(
                    action="other",
                    description=q[:240],
                    requested_by="executive_brain",
                )

            # 2. Decision and planning requests → record in DecisionEngine
            if req_type in {"decision", "planning"}:
                KERNEL.record_decision(
                    title=q[:120],
                    reason=getattr(plan, "guardian_reason", "") or req_type,
                    category="task" if req_type == "planning" else "other",
                    expected_outcome=getattr(plan, "executive_message", ""),
                )
        except Exception:
            pass
    brain_plan = {
        "request_type": plan.request_type,
        "ambiguous": plan.ambiguous,
        "clarification_needed": plan.clarification_needed,
        "clarification_question": plan.clarification_question,
        "context_links": plan.context_links,
        "context_summary": plan.context_summary,
        "plan_type": plan.plan_type,
        "steps": plan.steps,
        "selected_agent": plan.selected_agent,
        "supporting_agents": plan.supporting_agents,
        "agent_reasoning": plan.agent_reasoning,
        "autonomy_level": plan.autonomy_level,
        "should_remember": plan.should_remember,
        "memory_note": plan.memory_note,
        "executive_message": plan.executive_message,
    }
    execution_result = EXECUTIVE_BRAIN._execute_plan(
        q,
        plan,
        workspace_root=ROOT,
    )
    # ── 3b. Executive Kernel execution pipeline (when command has clear intent) ──
    # Must run BEFORE compose_final_reply so the reply can confirm the outcome.
    # SECURITY: ExecutionBoundary is the mandatory gate before execute_command.
    # It enforces Guardian fail-closed + conversational guard + auth chain.
    kernel_execution_trace: dict | None = worker_execution_trace
    kernel_execution_reply: str | None = worker_execution_reply
    kernel_detected_intent: str = "worker_dispatch" if requested_worker else "unknown"
    if KERNEL and not requested_worker:
        try:
            decomp = KERNEL.task_decomposer.decompose(q)
            kernel_detected_intent = str(decomp.get("intent", "unknown") or "unknown").strip().lower()
            if kernel_detected_intent != "unknown":
                _request_type_for_boundary = str(
                    getattr(plan, "request_type", "")
                ).strip().lower()
                kernel_execution_trace = KERNEL.execute_command(
                    q,
                    guardian=guardian,
                    request_type=_request_type_for_boundary or "execution",
                    requested_by="ask_endpoint",
                )
                final_exec = kernel_execution_trace.get("final", {})
                exec_results = final_exec.get("results") or []
                if final_exec.get("accepted"):
                    if kernel_detected_intent == "file_read":
                        read_result = next(
                            (
                                item for item in exec_results
                                if item.get("status") == "completed" and item.get("content") is not None
                            ),
                            None,
                        )
                        if read_result is not None:
                            kernel_execution_reply = str(read_result.get("content") or "")
                    else:
                        kernel_execution_reply = _format_kernel_execution_reply(
                            kernel_detected_intent,
                            final_exec,
                        )
                elif not final_exec.get("accepted"):
                    technical_reason = final_exec.get("technical_reason") or final_exec.get("reason") or "execution_failed"
                    kernel_execution_reply = (
                        "⚠️ لم يُنفّذ أمير الطلب التنفيذي. "
                        f"السبب التقني: {technical_reason}."
                    )
        except Exception as exc:
            if kernel_detected_intent != "unknown":
                kernel_execution_trace = {
                    "command": q,
                    "pipeline": [],
                    "final": {
                        "accepted": False,
                        "intent": kernel_detected_intent,
                        "reason": "execution_pipeline_exception",
                        "technical_reason": f"{type(exc).__name__}: {exc}",
                    },
                }
                kernel_execution_reply = (
                    "⚠️ تعذر تشغيل مسار التنفيذ. "
                    f"السبب التقني: {type(exc).__name__}: {exc}."
                )
    # ── 4. Compose fallback reply (used only if ECE is unavailable) ─────────────
    fallback_reply, reply_source = EXECUTIVE_BRAIN.compose_final_reply(
        reasoning_query,
        orchestrator_result,
        DOCUMENTS,
        existing_plan=plan,
        execution_result=execution_result,
        conversation_context=conversation_context,
        founder_context=founder_context,
        workspace_summary=workspace_summary,
        pending_approvals=pending_approvals,
        active_projects=active_projects,
        running_tasks=running_tasks,
        is_first_turn=is_first_turn,
    )
    # ── 5. P0.7 — Executive Conversation Engine is the sole response owner ──────
    conversation_result = {}
    final_reply = fallback_reply
    if EXECUTIVE_CONVERSATION_ENGINE:
        planner_state = EXECUTIVE_CONVERSATION_ENGINE.memory.plan(
            reasoning_query,
            active_projects=active_projects,
            running_tasks=running_tasks,
            pending_approvals=pending_approvals,
            workspace_summary=workspace_summary,
            executive_assessment=executive_assessment,
        )
        conversation_result = EXECUTIVE_CONVERSATION_ENGINE.execute(
            query=reasoning_query,
            draft_reply=fallback_reply,
            planner_state=planner_state,
            conversation_context=conversation_context,
            persistent_memory_block=persistent_memory_context,
            pending_approvals=pending_approvals,
            running_tasks=running_tasks,
            active_projects=active_projects,
            is_first_turn=is_first_turn,
            reasoning_output=reasoning_output,
        )
        final_reply = conversation_result.get("reply", fallback_reply)
        reply_source = conversation_result.get("engine", reply_source)

    # ── 5b. Kernel execution reply is advisory only (Guardian/ECE authoritative) ─
    # SECURITY: fail-closed — a missing, empty, or unknown guardian status is
    # treated as "deny", not as "pass".  Only an explicit "pass" string allows
    # the kernel execution reply to be presented to the user.
    _raw_guardian_status = (guardian or {}).get("status")
    _guardian_status = str(_raw_guardian_status).strip().lower() if _raw_guardian_status else "missing"
    _raw_reasoning_guardian = (reasoning_output or {}).get("reasoning", {}).get("guardian_status")
    _reasoning_guardian = str(_raw_reasoning_guardian).strip().lower() if _raw_reasoning_guardian else _guardian_status
    _request_type = str(
        ((reasoning_output or {}).get("reasoning", {}).get("request_type") or getattr(plan, "request_type", ""))
    ).strip().lower()
    _conversational_types = {"question", "greeting", "analysis", "memory", "creative"}
    _is_conversational_request = (_request_type in _conversational_types) or (not _request_type)
    _can_use_kernel_reply = (
        kernel_execution_reply is not None
        and _guardian_status == "pass"
        and _reasoning_guardian == "pass"
        and (
            not _is_conversational_request
            or kernel_detected_intent in KERNEL_ACTIONABLE_INTENTS
        )
    )
    if _can_use_kernel_reply:
        final_reply = kernel_execution_reply
        reply_source = "executive_kernel"
    elif kernel_detected_intent in KERNEL_ACTIONABLE_INTENTS and kernel_execution_trace is not None:
        # AEX-1: a known execution intent must not degrade to a conversational
        # answer when governance or infrastructure blocks execution.
        _technical_reason = (kernel_execution_trace.get("final") or {}).get("technical_reason") or (kernel_execution_trace.get("final") or {}).get("reason") or "execution_not_completed"
        final_reply = f"⚠️ الطلب تنفيذي معروف لكنه لم يكتمل. السبب التقني: {_technical_reason}."
        reply_source = "executive_kernel_blocked"

    # ── 6. AOS Kernel: record assistant reply in session context ──────────────
    if KERNEL:
        try:
            KERNEL.after_request(final_reply)
        except Exception:
            pass

    if not RESPONSE_FORMATTER:
        raise HTTPException(status_code=500, detail="Response Composer is unavailable")

    composer_payload = {
        "reply": final_reply,
        "message": final_reply,
        "intent": orchestrator_result.get("intent"),
        "agent_result": orchestrator_result.get("agent_result"),
        "agent_brain_payload": orchestrator_result.get("agent_brain_payload"),
    }
    if DEBUG_MODE:
        trace_steps = orchestrator_result.get("orchestrator", {}).get("trace", [])
        routing = orchestrator_result.get("routing") or {}
        orchestrator_agent = orchestrator_result.get("selected_agent")
        executive_agent = brain_plan.get("selected_agent") if brain_plan else None
        debug_trace = {
            "router": {
                "intent": routing.get("intent"),
                "agent": routing.get("agent"),
                "confidence": routing.get("confidence"),
                "reason": routing.get("reason"),
                "identity_layer": routing.get("identity_layer"),
            },
            "orchestrator": {
                "selected_agent": orchestrator_agent,
                "trace": trace_steps,
            },
            "executive": {
                "selected_agent": executive_agent,
                "reply_generated_by": reply_source,
                "single_brain_mode": bool(getattr(EXECUTIVE_BRAIN, "_single_brain_mode", False)),
                "aos_kernel": "active" if KERNEL else "inactive",
                "executive_conversation_engine": conversation_result,
            },
        }
        _log("ask_debug_trace", request_id=request_id, trace=debug_trace)
        if project_manager:
            _log("ask_project_manager", request_id=request_id, project_manager=project_manager)
        if autonomy_plan:
            _log("ask_autonomy_plan", request_id=request_id, autonomy_plan=autonomy_plan)

    try:
        user_payload = RESPONSE_FORMATTER.format_payload(composer_payload)
    except Exception:
        user_payload = {
            "reply": "أنا معك.",
            "message": "أنا معك.",
            "assistant": "أمير",
        }
    if (
        _can_use_kernel_reply
        and kernel_detected_intent == "file_read"
        and isinstance(kernel_execution_reply, str)
        and kernel_execution_reply
    ):
        user_payload["reply"] = kernel_execution_reply
        user_payload["message"] = kernel_execution_reply
    user_payload.update(public_runtime_identity(workspace_root=REPO_ROOT))
    user_payload["request_id"] = request_id
    user_payload["attachments"] = attached_files
    if attached_files:
        user_payload["attachment_audit"] = CHAT_MEDIA.audit_summary(attachment_ids)
    if kernel_execution_trace is not None:
        user_payload["execution_trace"] = kernel_execution_trace
        user_payload["run_trace"] = kernel_execution_trace
        _preview_path = kernel_execution_trace.get("final", {}).get("preview_path") or ""
        if _preview_path.startswith("09_Assets/runtime_workspace/projects/"):
            _slug = _preview_path[len("09_Assets/runtime_workspace/projects/"):].split("/")[0]
            if _slug:
                user_payload["preview_url"] = f"/preview/projects/{_slug}"
        elif _preview_path.startswith("09_Assets/runtime_workspace/home/"):
            user_payload["preview_url"] = "/preview"
    _log("ask_completed", request_id=request_id)
    return utf8_json_response(user_payload, headers=runtime_headers(workspace_root=REPO_ROOT))

@app.post('/ask/trace')
async def ask_trace(request: Request):
    """
    Full pipeline trace endpoint — demonstrates every stage of the runtime.

    P0.7 trace schema:
      1. kernel_state_before           — Kernel state snapshot before the request
      2. executive_brain_reasoning     — Executive Brain reasoning output (no visible text)
      3. planner_output                — Planner: objectives, priorities, risks, recommendations
      4. final_response                — Final response (owned solely by ECE)
      5. response_owner                — Always "ExecutiveConversationEngine"
    """
    request_id = str(uuid.uuid4())
    raw = await request.body()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty body")

    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=400, detail="Invalid UTF-8 JSON body") from exc

    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Expected JSON object")

    req = AskRequest(**payload)
    q = req.query.strip() if isinstance(req.query, str) else ''
    if not q:
        raise HTTPException(status_code=400, detail="Empty query")

    _log("ask_trace_received", request_id=request_id)

    # ── 1. Capture Kernel state BEFORE the request ─────────────────────────────
    kernel_state_before: dict = {}
    conversation_context = ""
    founder_context = ""
    workspace_summary = ""
    pending_approvals: list = []
    active_projects: list = []
    running_tasks: list = []
    executive_assessment = ""
    persistent_memory_context = ""
    is_first_turn = False

    if KERNEL:
        try:
            # Ensure kernel is booted so state is populated before we snapshot it
            if not KERNEL._initialized:
                KERNEL.boot()
            # Snapshot state *before* before_request mutates session context
            kernel_state_before = {
                "active_projects": list(KERNEL.state.active_projects),
                "pending_approvals": list(KERNEL.state.pending_approvals),
                "running_tasks": list(KERNEL.state.running_tasks),
                "executive_assessment": KERNEL.state.executive_assessment,
                "workspace_summary": KERNEL.state.workspace_summary,
                "session_count": KERNEL.state.session_count,
                "runtime_status": KERNEL.state.runtime_status,
                "last_session_at": KERNEL.state.last_session_at,
                "conversation_memory_snapshot": KERNEL.conversation_memory.snapshot(),
            }
            ctx = KERNEL.before_request(q)
            conversation_context = ctx.get("conversation_context", "")
            founder_context = ctx.get("founder_context", "")
            workspace_summary = ctx.get("workspace_summary", "")
            pending_approvals = ctx.get("pending_approvals", [])
            active_projects = ctx.get("active_projects", [])
            running_tasks = ctx.get("running_tasks", [])
            executive_assessment = ctx.get("executive_assessment", "")
            persistent_memory_context = ctx.get("persistent_memory_context", "")
            is_first_turn = ctx.get("is_first_turn", False)
        except Exception as exc:
            kernel_state_before["error"] = "kernel_context_unavailable"

    # ── 2. Orchestrator ────────────────────────────────────────────────────────
    orchestrator_result = ORCHESTRATOR.answer(q, req.max_results)

    if not EXECUTIVE_BRAIN:
        raise HTTPException(status_code=500, detail="Executive Brain is unavailable")

    guardian = orchestrator_result.get("guardian", {})
    routing = orchestrator_result.get("routing") or {}

    # ── 3. Executive Brain → Reasoning Only (P0.7) ────────────────────────────
    # P0.2 — compute plan once and pass it to get_reasoning_output
    plan = EXECUTIVE_BRAIN.think(
        q,
        DOCUMENTS,
        guardian_result=guardian,
        routing_hint=routing,
    )
    reasoning_output = EXECUTIVE_BRAIN.get_reasoning_output(
        q,
        DOCUMENTS,
        guardian_result=guardian,
        routing_hint=routing,
        existing_plan=plan,
    )
    reasoning_output["_plan"] = plan

    # ── P0.1 — Governance wiring (trace endpoint mirrors /ask) ────────────────
    if KERNEL:
        try:
            g_status = getattr(plan, "guardian_status", "pass")
            req_type = getattr(plan, "request_type", "")
            if g_status == "needs_approval":
                KERNEL.request_approval(
                    action="other",
                    description=q[:240],
                    requested_by="executive_brain",
                )
            if req_type in {"decision", "planning"}:
                KERNEL.record_decision(
                    title=q[:120],
                    reason=getattr(plan, "guardian_reason", "") or req_type,
                    category="task" if req_type == "planning" else "other",
                    expected_outcome=getattr(plan, "executive_message", ""),
                )
        except Exception:
            pass

    execution_result = EXECUTIVE_BRAIN._execute_plan(q, plan, workspace_root=ROOT)

    # ── 4. Planner → Executive State (P0.7) ───────────────────────────────────
    planner_output: dict = {}
    conversation_result: dict = {}
    final_reply = "أنا معك."

    if EXECUTIVE_CONVERSATION_ENGINE:
        planner_state = EXECUTIVE_CONVERSATION_ENGINE.memory.plan(
            q,
            active_projects=active_projects,
            running_tasks=running_tasks,
            pending_approvals=pending_approvals,
            workspace_summary=workspace_summary,
            executive_assessment=executive_assessment,
        )
        # P0.7 Planner output: objectives, priorities, risks, recommendations only
        planner_output = {
            "objectives": list(planner_state.objectives or []),
            "priorities": list(planner_state.priorities or []),
            "risks": list(planner_state.risks or []),
            "recommendations": list(planner_state.recommendations or []),
        }

        # ── 5. Executive Conversation Engine → Final Response Owner (P0.7) ───
        conversation_result = EXECUTIVE_CONVERSATION_ENGINE.execute(
            query=q,
            planner_state=planner_state,
            conversation_context=conversation_context,
            persistent_memory_block=persistent_memory_context,
            pending_approvals=pending_approvals,
            running_tasks=running_tasks,
            active_projects=active_projects,
            is_first_turn=is_first_turn,
            dry_run=True,
            reasoning_output=reasoning_output,
        )
        final_reply = conversation_result.get("reply", final_reply)

    # ── 6. Kernel after_request ────────────────────────────────────────────────
    if KERNEL:
        try:
            KERNEL.after_request(final_reply)
        except Exception:
            pass

    # ── 7. Response Formatter → Formatting Only (P0.7) ───────────────────────
    if not RESPONSE_FORMATTER:
        raise HTTPException(status_code=500, detail="Response Composer is unavailable")

    composer_payload = {
        "reply": final_reply,
        "message": final_reply,
        "intent": orchestrator_result.get("intent"),
        "agent_result": orchestrator_result.get("agent_result"),
        "agent_brain_payload": orchestrator_result.get("agent_brain_payload"),
    }
    try:
        user_payload = RESPONSE_FORMATTER.format_payload(composer_payload)
    except Exception:
        user_payload = {
            "reply": "أنا معك.",
            "message": "أنا معك.",
            "assistant": "أمير",
        }

    formatted_reply = user_payload.get("reply", "")

    # ── 8. P0.7 Trace Response ────────────────────────────────────────────────
    # Fields: executive_brain_reasoning, planner_output (objectives/priorities/risks/recommendations),
    # final_response (ECE-owned), response_owner
    # Removed: was_modified, draft_reply, append/prepend traces
    trace_response = {
        "request_id": request_id,
        "query": q,
        "kernel_state_before": kernel_state_before,
        "executive_brain_reasoning": {
            "role": "Executive Brain → Reasoning Only",
            "reasoning": reasoning_output.get("reasoning", {}),
            "executive_state": reasoning_output.get("executive_state", {}),
        },
        "planner_output": {
            "role": "Planner → Executive State",
            **planner_output,
        },
        "final_response": {
            "role": "Executive Conversation Engine → Final Response Owner",
            "reply": formatted_reply,
            "response_owner": "ExecutiveConversationEngine",
        },
        "formatter": {
            "role": "Formatter → Formatting Only",
        },
        "response_owner": "ExecutiveConversationEngine",
    }
    trace_response.update(public_runtime_identity(workspace_root=REPO_ROOT))
    _log("ask_trace_completed", request_id=request_id, response_owner="ExecutiveConversationEngine")
    return utf8_json_response(trace_response, headers=runtime_headers(workspace_root=REPO_ROOT))


@app.get('/docs')
async def docs():
    return {"count": len(DOCUMENTS)}

def _load_project_store() -> list[dict]:
    store_path = os.path.join(ROOT, ".ameer", "projects.json")
    if not os.path.exists(store_path):
        return []
    try:
        with open(store_path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
            if isinstance(payload, list):
                return payload
    except Exception:
        return []
    return []


def _save_project_store(projects: list[dict]) -> None:
    store_path = os.path.join(ROOT, ".ameer", "projects.json")
    os.makedirs(os.path.dirname(store_path), exist_ok=True)
    with open(store_path, "w", encoding="utf-8") as handle:
        json.dump(projects, handle, ensure_ascii=False, indent=2)


def _load_plan_store() -> list[dict]:
    store_path = os.path.join(ROOT, ".ameer", "plans.json")
    if not os.path.exists(store_path):
        return []
    try:
        with open(store_path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
            if isinstance(payload, list):
                return payload
    except Exception:
        return []
    return []


def _save_plan_store(plans: list[dict]) -> None:
    store_path = os.path.join(ROOT, ".ameer", "plans.json")
    os.makedirs(os.path.dirname(store_path), exist_ok=True)
    with open(store_path, "w", encoding="utf-8") as handle:
        json.dump(plans, handle, ensure_ascii=False, indent=2)


def _derive_autonomy_steps(query: str) -> list[str]:
    text = (query or "").lower()
    steps: list[str] = []
    if any(term in text for term in ["memory", "ذاكرة", "تذكر", "remember"]):
        steps.append("Strengthen long-term memory capture")
    if any(term in text for term in ["plan", "خطة", "planning", "خطط"]):
        steps.append("Improve planning and decomposition")
    if any(term in text for term in ["tool", "أداة", "execute", "نفذ", "execution"]):
        steps.append("Expand reliable tool execution")
    if any(term in text for term in ["document", "مستند", "workspace", "مساحة العمل", "workspace"]):
        steps.append("Increase workspace and document understanding")
    if any(term in text for term in ["autonom", "استقلال", "self", "ذاتي"]):
        steps.append("Raise autonomy and self-correction")
    if not steps:
        steps = [
            "Clarify the objective",
            "Gather relevant context",
            "Act and evaluate the result",
        ]
    return steps[:5]


def _record_autonomy_plan(query: str, goal: str | None = None) -> dict:
    normalized_goal = (goal or "autonomy").strip() or "autonomy"
    plan = {
        "query": query.strip(),
        "goal": normalized_goal,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "steps": _derive_autonomy_steps(query),
    }
    plans = _load_plan_store()
    plans.append(plan)
    _save_plan_store(plans)
    return plan


@app.post('/autonomy/plan')
async def store_autonomy_plan(payload: AutonomyPlanRequest):
    query = payload.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Empty autonomy plan query")
    plan = _record_autonomy_plan(query, payload.goal)
    return {"stored": True, "plan": plan, "plans": _load_plan_store()}


@app.get('/health')
async def health():
    meta = runtime_metadata(workspace_root=REPO_ROOT)
    payload = {
        "status": meta["status"],
        "build": meta["build"],
        "build_id": meta["build_id"],
        "commit": meta["commit"],
        "commit_source": meta.get("commit_source", "unknown"),
        "deployment_id": meta.get("deployment_id", ""),
        "deployment_provider": meta.get("deployment_provider", "unknown"),
        "started_at": meta["started_at"],
        "documents": len(DOCUMENTS),
        "ameer_status": {
            "Server": "Online",
            "Documents": "Ready",
            "Brain": "Ready",
            "Memory": "Ready",
            "Projects": "Ready",
        },
        "worker_runtime": KERNEL.worker_runtime.snapshot() if KERNEL else {"status": "unavailable"},
    }
    return utf8_json_response(payload, headers=runtime_headers(workspace_root=REPO_ROOT))


@app.get('/workers/runtime')
async def workers_runtime():
    """Read-only worker/model availability; registration is not readiness."""
    if not KERNEL:
        return utf8_json_response({"status": "unavailable", "reason": "kernel_inactive"}, status_code=503)
    return utf8_json_response({"status": "ok", "runtime": KERNEL.worker_runtime.snapshot()})


@app.get('/agent/authority')
async def agent_authority():
    """Expose the governed reporting chain without exposing credentials."""
    authority = KERNEL.orchestrator.authority() if KERNEL and hasattr(KERNEL, "orchestrator") else {}
    return utf8_json_response({
        "status": "ok",
        "executive": "ameer",
        "orchestrator": "ExecutiveOrchestrator",
        "workers": sorted(DEFAULT_WORKERS),
        "reporting_chain": "user/founder -> ameer -> workers -> ameer -> user/founder",
        "worker_direct_founder_contact": False,
        "final_approval_owner": "founder",
        "authority": authority,
        "message_bus": MESSAGE_BUS.snapshot() if MESSAGE_BUS else {"status": "unavailable"},
    })


@app.get('/orchestrator/status')
async def orchestrator_status():
    if not KERNEL or not hasattr(KERNEL, "orchestrator"):
        return utf8_json_response({"status": "unavailable"}, status_code=503)
    return utf8_json_response(KERNEL.orchestrator.authority())


@app.get('/audit/execution')
async def execution_audit(correlation_id: str | None = None, limit: int = 100):
    if not KERNEL or not hasattr(KERNEL, "orchestrator"):
        return utf8_json_response({"status": "unavailable", "events": []}, status_code=503)
    return utf8_json_response({"status": "ok", "audit": KERNEL.orchestrator.audit_snapshot(), "events": KERNEL.orchestrator.audit_events(correlation_id=correlation_id, limit=limit)})


@app.get('/costs/summary')
async def costs_summary():
    """Read-only cost totals grouped by agent; never exposes prompts or credentials."""
    if not KERNEL or not getattr(KERNEL, "worker_runtime", None):
        return utf8_json_response({"status": "unavailable", "reason": "worker_runtime_unavailable"}, status_code=503)
    ledger = KERNEL.worker_runtime.cost_ledger
    return utf8_json_response(ledger.summary())


@app.get('/costs/usage')
async def costs_usage(agent_id: str | None = None, task_id: str | None = None, limit: int = 100):
    """Read-only usage events linked to task/run/agent identifiers."""
    if not KERNEL or not getattr(KERNEL, "worker_runtime", None):
        return utf8_json_response({"status": "unavailable", "events": []}, status_code=503)
    limit = max(1, min(int(limit), 1000))
    ledger = KERNEL.worker_runtime.cost_ledger
    return utf8_json_response(ledger.snapshot(agent_id=agent_id, task_id=task_id, limit=limit))


@app.get('/costs/health')
async def costs_health():
    if not KERNEL or not getattr(KERNEL, "worker_runtime", None):
        return utf8_json_response({"status": "unavailable"}, status_code=503)
    return utf8_json_response(KERNEL.worker_runtime.cost_ledger.health())


@app.get('/school/dashboard')
async def school_dashboard():
    """Return the private school project's live follow-up and weekly plan."""
    if SCHOOL_OPERATIONS is None:
        return utf8_json_response({"status": "unavailable"}, status_code=503)
    return utf8_json_response({
        "status": "ok",
        "categories": SCHOOL_TASK_CATEGORIES,
        **SCHOOL_OPERATIONS.dashboard(),
    })


@app.post('/school/tasks')
async def create_school_task(request: Request):
    if SCHOOL_OPERATIONS is None:
        return utf8_json_response({"status": "unavailable"}, status_code=503)
    try:
        body = await request.json()
    except Exception:
        return utf8_json_response({"status": "invalid_request", "reason": "invalid_json"}, status_code=400)
    try:
        task = SCHOOL_OPERATIONS.add_task(
            body.get("title", ""),
            due_at=str(body.get("due_at") or ""),
            priority=str(body.get("priority") or "normal"),
            category=str(body.get("category") or "general"),
            missing_inputs=str(body.get("missing_inputs") or ""),
            notes=str(body.get("notes") or ""),
        )
    except ValueError as exc:
        return utf8_json_response({"status": "invalid_request", "reason": str(exc)}, status_code=422)
    return utf8_json_response({"status": "created", "task": task}, status_code=201)


@app.patch('/school/tasks/{task_id}')
async def update_school_task(task_id: int, request: Request):
    if SCHOOL_OPERATIONS is None:
        return utf8_json_response({"status": "unavailable"}, status_code=503)
    try:
        changes = await request.json()
        if not isinstance(changes, dict):
            raise ValueError("changes_must_be_an_object")
        result = SCHOOL_OPERATIONS.update_task(task_id, changes)
    except KeyError:
        return utf8_json_response({"status": "not_found", "reason": "school_task_not_found"}, status_code=404)
    except ValueError as exc:
        return utf8_json_response({"status": "invalid_request", "reason": str(exc)}, status_code=422)
    except Exception:
        return utf8_json_response({"status": "invalid_request", "reason": "invalid_json"}, status_code=400)
    return utf8_json_response(result)


@app.get('/center/profile')
async def center_profile():
    if BUSINESS_OPERATIONS is None:
        return utf8_json_response({"status": "unavailable"}, status_code=503)
    return utf8_json_response({"status": "ok", "center": BUSINESS_OPERATIONS.center_profile()})


@app.get('/center/dashboard')
async def center_dashboard():
    if BUSINESS_OPERATIONS is None:
        return utf8_json_response({"status": "unavailable"}, status_code=503)
    return utf8_json_response({"status": "ok", **BUSINESS_OPERATIONS.store_dashboard()})


@app.get('/center/inventory')
async def center_inventory():
    if BUSINESS_OPERATIONS is None:
        return utf8_json_response({"status": "unavailable", "items": []}, status_code=503)
    return utf8_json_response({"status": "ok", "items": BUSINESS_OPERATIONS.list_products(), "low_stock": BUSINESS_OPERATIONS.low_stock()})


@app.get('/center/employees')
async def center_employees():
    if BUSINESS_OPERATIONS is None:
        return utf8_json_response({"status": "unavailable", "employees": []}, status_code=503)
    return utf8_json_response({"status": "ok", "employees": BUSINESS_OPERATIONS.list_employees(status=None)})


@app.get('/center/bookings')
async def center_bookings(limit: int = 100):
    if BUSINESS_OPERATIONS is None:
        return utf8_json_response({"status": "unavailable", "bookings": []}, status_code=503)
    return utf8_json_response({"status": "ok", "bookings": BUSINESS_OPERATIONS.list_bookings(limit=limit)})


@app.get('/center/bookings/available')
async def center_available_bookings(limit: int = 100):
    """Read-only availability queue; only explicitly available/pending/held records."""
    if BUSINESS_OPERATIONS is None:
        return utf8_json_response({"status": "unavailable", "bookings": []}, status_code=503)
    return utf8_json_response({"status": "ok", "bookings": BUSINESS_OPERATIONS.list_available_bookings(limit=limit)})


@app.post('/booking/confirm')
@app.post('/center/bookings/confirm')
async def confirm_center_booking(request: Request):
    """Ameer auto-confirms a normal available booking without founder approval."""
    if BUSINESS_OPERATIONS is None:
        return utf8_json_response({"status": "unavailable"}, status_code=503)
    try:
        body = await request.json()
    except Exception:
        return utf8_json_response({"status": "invalid_request", "reason": "invalid_json"}, status_code=400)
    if str(body.get("actor") or "").strip().lower() != "ameer":
        return utf8_json_response({"status": "blocked", "reason": "ameer_authority_required"}, status_code=403)
    title = str(body.get("title") or "").strip()
    starts_at = str(body.get("starts_at") or "").strip()
    if not title or not starts_at:
        return utf8_json_response({"status": "invalid_request", "reason": "title_and_starts_at_required"}, status_code=422)
    try:
        booking = BUSINESS_OPERATIONS.confirm_booking_for_ameer(
            title,
            starts_at,
            ends_at=str(body.get("ends_at") or ""),
            customer_id=body.get("customer_id"),
            employee_id=body.get("employee_id"),
            notes=str(body.get("notes") or ""),
        )
    except ValueError as exc:
        if str(exc).startswith("booking_unavailable:"):
            return utf8_json_response({"status": "unavailable", "reason": str(exc), "founder_approval_required": False}, status_code=409)
        return utf8_json_response({"status": "invalid_request", "reason": str(exc)}, status_code=422)
    return utf8_json_response({"status": "confirmed", "booking": booking, "confirmed_by": "ameer", "founder_approval_required": False})


@app.post('/test/booking/confirm')
async def test_confirm_booking(request: Request):
    """Run booking confirmation scenarios only in an explicitly isolated test environment."""
    test_mode = (os.getenv("AMEER_TEST_MODE") or "").strip().lower() == "true"
    environment = (os.getenv("AMEER_ENV") or os.getenv("ENVIRONMENT") or "production").strip().lower()
    if not test_mode or environment in {"production", "prod"}:
        return utf8_json_response({"status": "blocked", "reason": "test_endpoint_disabled_in_production"}, status_code=404)
    try:
        body = await request.json()
    except Exception:
        return utf8_json_response({"status": "invalid_request", "reason": "invalid_json"}, status_code=400)
    scenario = str(body.get("scenario") or "available").strip().lower()
    actor = str(body.get("actor") or "").strip().lower()
    if scenario not in {"available", "conflict"}:
        return utf8_json_response({"status": "invalid_request", "reason": "unknown_fixture_scenario"}, status_code=422)
    if actor != "ameer":
        return utf8_json_response({"status": "blocked", "reason": "ameer_authority_required", "fixture": True}, status_code=403)
    old_data_dir = os.environ.get("AMEER_DATA_DIR")
    try:
        with tempfile.TemporaryDirectory(prefix="ameer-booking-fixture-") as fixture_root:
            os.environ["AMEER_DATA_DIR"] = fixture_root
            fixture_store = BusinessOperations(fixture_root)
            employee = fixture_store.add_employee("Fixture Employee", role="beauty")
            payload = {
                "title": "Fixture booking",
                "starts_at": "2035-01-01T10:00:00Z",
                "ends_at": "2035-01-01T11:00:00Z",
                "employee_id": employee["id"],
            }
            if scenario == "conflict":
                fixture_store.confirm_booking_for_ameer(**payload)
                payload["title"] = "Fixture conflicting booking"
                payload["starts_at"] = "2035-01-01T10:30:00Z"
                payload["ends_at"] = "2035-01-01T11:30:00Z"
            try:
                booking = fixture_store.confirm_booking_for_ameer(**payload)
            except ValueError as exc:
                if str(exc).startswith("booking_unavailable:"):
                    return utf8_json_response({"status": "unavailable", "reason": "booking_conflict_detected", "fixture": True}, status_code=409)
                return utf8_json_response({"status": "invalid_request", "reason": str(exc), "fixture": True}, status_code=422)
            return utf8_json_response({"status": "confirmed", "booking": booking, "confirmed_by": "ameer", "fixture": True}, status_code=200)
    finally:
        if old_data_dir is None:
            os.environ.pop("AMEER_DATA_DIR", None)
        else:
            os.environ["AMEER_DATA_DIR"] = old_data_dir


@app.get('/center/customers')
async def center_customers():
    if BUSINESS_OPERATIONS is None:
        return utf8_json_response({"status": "unavailable", "customers": []}, status_code=503)
    return utf8_json_response({"status": "ok", "customers": BUSINESS_OPERATIONS.list_customers()})


@app.get('/agent/messages')
async def agent_messages(actor: str | None = None, limit: int = 100):
    if MESSAGE_BUS is None:
        return utf8_json_response({"status": "unavailable", "messages": []}, status_code=503)
    try:
        messages = MESSAGE_BUS.list(actor=actor, limit=limit)
    except ValueError:
        return utf8_json_response({"status": "invalid_actor"}, status_code=422)
    return utf8_json_response({"status": "ok", "messages": messages, "count": len(messages)})


@app.post('/agent/messages')
async def post_agent_message(request: Request):
    """Accept user/founder messages into Ameer's inbox; workers cannot impersonate the user."""
    if MESSAGE_BUS is None:
        return utf8_json_response({"status": "unavailable"}, status_code=503)
    try:
        body = await request.json()
    except Exception:
        return utf8_json_response({"status": "invalid_request", "reason": "invalid_json"}, status_code=400)
    sender = str(body.get("sender") or "user").strip().lower()
    if sender != "user":
        return utf8_json_response({"status": "blocked", "reason": "authenticated_founder_channel_required"}, status_code=403)
    try:
        message = MESSAGE_BUS.send(
            sender=sender,
            recipient="ameer",
            body=str(body.get("body") or body.get("message") or ""),
            kind=str(body.get("kind") or "user_command"),
            metadata={"channel": body.get("channel", "web"), "request_id": body.get("request_id")},
        )
    except PermissionError as exc:
        return utf8_json_response({"status": "blocked", "reason": str(exc)}, status_code=403)
    except ValueError as exc:
        return utf8_json_response({"status": "invalid_request", "reason": str(exc)}, status_code=422)
    return utf8_json_response({"status": "accepted", "message": message})


@app.post('/agent/delegate')
async def delegate_agent_task(request: Request):
    """Ameer delegates internal work to a worker and reports the result back."""
    if not KERNEL or MESSAGE_BUS is None:
        return utf8_json_response({"status": "unavailable"}, status_code=503)
    try:
        body = await request.json()
    except Exception:
        return utf8_json_response({"status": "invalid_request", "reason": "invalid_json"}, status_code=400)
    worker_id = str(body.get("worker_id") or "").strip().lower()
    objective = str(body.get("objective") or "").strip()
    ameer_review = body.get("ameer_review") is True
    external_effect = body.get("external_effect") is True
    if worker_id not in DEFAULT_WORKERS or not objective:
        return utf8_json_response({"status": "invalid_request", "reason": "worker_id_and_objective_required"}, status_code=422)
    if not ameer_review:
        return utf8_json_response({"status": "pending", "reason": "ameer_review_required", "next": "Ameer must review and open the execution lane"}, status_code=422)
    delegation = MESSAGE_BUS.send(sender="ameer", recipient=worker_id, body=objective, kind="delegation", metadata={"reviewed_by": "ameer", "external_effect": external_effect})
    if external_effect:
        approval_id = KERNEL.request_approval(action=str(body.get("approval_action") or "external"), description=objective, requested_by="ameer")
        notice = MESSAGE_BUS.send(sender="ameer", recipient="user", body=f"يحتاج هذا الإجراء موافقتك النهائية: {objective}", kind="final_approval_request", metadata={"approval_id": approval_id, "worker_id": worker_id})
        return utf8_json_response({"status": "pending_final_approval", "approval_id": approval_id, "delegation": delegation, "notice": notice}, status_code=202)
    orchestrated = KERNEL.orchestrator.execute_delegation(worker_id, objective, {"mode": "ameer_delegation", "delegation_id": delegation["message_id"], "ameer_review": True, "external_effect": False})
    result = orchestrated.get("worker_result", orchestrated)
    report = MESSAGE_BUS.send(sender=worker_id, recipient="ameer", body=json.dumps(result, ensure_ascii=False), kind="worker_report", metadata={"run_id": result.get("run_id"), "status": result.get("status"), "correlation_id": orchestrated.get("correlation_id")})
    user_notice = MESSAGE_BUS.send(sender="ameer", recipient="user", body=f"تقرير العامل {worker_id}: {result.get('status')}", kind="worker_result", metadata={"run_id": result.get("run_id"), "worker_id": worker_id, "correlation_id": orchestrated.get("correlation_id")})
    return utf8_json_response({"status": result.get("status"), "delegation": orchestrated.get("delegation", delegation), "worker_result": result, "worker_report": report, "user_notice": user_notice, "correlation_id": orchestrated.get("correlation_id")}, status_code=200 if result.get("status") == "completed" else 422)


@app.get('/build-info')
async def build_info():
    """Public, non-secret build identity used to verify deployment provenance."""
    meta = runtime_metadata(workspace_root=REPO_ROOT)
    return utf8_json_response(
        {
            "status": meta["status"],
            "build": meta["build"],
            "build_id": meta["build_id"],
            "commit": meta["commit"],
            "commit_source": meta.get("commit_source", "unknown"),
            "deployment_id": meta.get("deployment_id", ""),
            "deployment_provider": meta.get("deployment_provider", "unknown"),
            "started_at": meta["started_at"],
        },
        headers=runtime_headers(workspace_root=REPO_ROOT),
    )


@app.get('/documents/search')
async def search_documents(q: str):
    refresh_documents()
    if not q or not q.strip():
        return {"results": []}
    query = q.strip()
    matches = []
    for doc in DOCUMENTS:
        text = doc.get("text", "")
        if query.lower() in text.lower() or query.lower() in doc.get("path", "").lower():
            excerpt = text[:220].replace('\n', ' ')
            matches.append({"path": doc.get("path"), "excerpt": excerpt})
    return {"query": query, "results": matches[:8]}


@app.post('/memory')
async def save_memory(payload: MemoryRequest):
    if not KERNEL:
        return utf8_json_response({"status": "unavailable"}, status_code=503)
    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Empty memory text")

    try:
        result = KERNEL.memory_governance.submit_candidate(
            content=text,
            source=(payload.source or "founder"),
            requested_layer=(payload.target_layer or "founder_memory"),
            confidence=payload.confidence,
            origin_context={"endpoint": "/memory"},
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="invalid memory candidate")
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail="memory policy violation")

    if result.get("saved"):
        refresh_documents()
    return utf8_json_response(result)


@app.get('/memory/governance')
async def get_memory_governance_snapshot():
    if not KERNEL:
        return utf8_json_response({"status": "unavailable"}, status_code=503)
    return utf8_json_response(KERNEL.memory_governance.snapshot())


@app.get('/memory/candidates')
async def get_memory_candidates():
    if not KERNEL:
        return utf8_json_response({"status": "unavailable"}, status_code=503)
    return utf8_json_response({"pending_candidates": KERNEL.memory_governance.pending_candidates()})


@app.get('/memory/items/{layer}')
async def get_memory_items(layer: str):
    if not KERNEL:
        return utf8_json_response({"status": "unavailable"}, status_code=503)
    return utf8_json_response({"layer": layer, "items": KERNEL.memory_governance.list_items(layer)})


@app.delete('/memory/items/{layer}/{item_id}')
async def delete_memory_item(layer: str, item_id: str):
    if not KERNEL:
        return utf8_json_response({"status": "unavailable"}, status_code=503)
    deleted = KERNEL.memory_governance.delete_item(layer, item_id)
    if not deleted:
        return utf8_json_response({"error": "item not found or cannot be deleted"}, status_code=404)
    return utf8_json_response({"deleted": True, "layer": layer, "item_id": item_id})


@app.post('/knowledge/promote')
async def promote_learned_knowledge(payload: KnowledgePromotionRequest):
    if not KERNEL:
        return utf8_json_response({"status": "unavailable"}, status_code=503)
    try:
        promoted = KERNEL.memory_governance.promote_learned_to_core(
            payload.item_id,
            reason=payload.reason,
            approved_by=payload.approved_by,
        )
    except ValueError as exc:
        return utf8_json_response({"error": "invalid feedback payload"}, status_code=422)
    return utf8_json_response({"promoted": True, "record": promoted})


@app.get('/shadow/foundation')
async def shadow_foundation_snapshot():
    """Read-only snapshot of Shadow identity, projects, roles, and default policies."""
    if not KERNEL or not getattr(KERNEL, "shadow_foundation", None):
        return utf8_json_response({"status": "unavailable"}, status_code=503)
    return utf8_json_response({"status": "ok", **KERNEL.shadow_foundation.snapshot()})


@app.get('/shadow/projects')
async def shadow_projects(parent_id: str | None = None):
    """Read-only project registry; mutations remain behind the governed project flow."""
    if not KERNEL or not getattr(KERNEL, "shadow_foundation", None):
        return utf8_json_response({"status": "unavailable"}, status_code=503)
    return utf8_json_response({"status": "ok", "projects": KERNEL.shadow_foundation.list_projects(parent_id=parent_id)})


@app.get('/test/commerce/snapshot')
async def test_commerce_snapshot():
    if not COMMERCE_TEST:
        return utf8_json_response({"status": "unavailable"}, status_code=503)
    return utf8_json_response({"status": "ok", **COMMERCE_TEST.snapshot()})


@app.post('/test/commerce/orders')
async def test_commerce_create_order(payload: dict):
    if not COMMERCE_TEST:
        return utf8_json_response({"status": "unavailable"}, status_code=503)
    if not payload.get("customer_name") or payload.get("total") is None:
        return utf8_json_response({"status": "invalid", "required": ["customer_name", "total"]}, status_code=422)
    try:
        order = COMMERCE_TEST.create_order(
            customer_name=str(payload["customer_name"]),
            total=float(payload["total"]),
            currency=str(payload.get("currency", "SAR")),
        )
    except (TypeError, ValueError) as exc:
        return utf8_json_response({"status": "invalid", "reason": str(exc)}, status_code=422)
    return utf8_json_response({"status": "created", "mode": "test", "no_real_money": True, "order": order}, status_code=201)


@app.post('/test/commerce/orders/{order_id}/payment-session')
async def test_commerce_payment_session(order_id: str):
    if not COMMERCE_TEST:
        return utf8_json_response({"status": "unavailable"}, status_code=503)
    try:
        session = COMMERCE_TEST.create_payment_session(order_id)
    except KeyError as exc:
        return utf8_json_response({"status": "not_found", "reason": str(exc)}, status_code=404)
    except ValueError as exc:
        return utf8_json_response({"status": "invalid", "reason": str(exc)}, status_code=409)
    return utf8_json_response({"status": "created", **session})


@app.post('/test/commerce/webhooks/payment')
async def test_commerce_payment_webhook(payload: dict):
    if not COMMERCE_TEST:
        return utf8_json_response({"status": "unavailable"}, status_code=503)
    required = ("event_id", "order_id", "event_type", "status")
    missing = [key for key in required if not payload.get(key)]
    if missing:
        return utf8_json_response({"status": "invalid", "missing": missing}, status_code=422)
    try:
        result = COMMERCE_TEST.process_payment_webhook(
            event_id=str(payload["event_id"]), order_id=str(payload["order_id"]),
            event_type=str(payload["event_type"]), status=str(payload["status"]),
            payload=payload, provider=str(payload.get("provider", "test_gateway")),
        )
    except KeyError as exc:
        return utf8_json_response({"status": "not_found", "reason": str(exc)}, status_code=404)
    except ValueError as exc:
        return utf8_json_response({"status": "invalid", "reason": str(exc)}, status_code=422)
    return utf8_json_response(result)


@app.post('/test/commerce/webhooks/tap')
async def test_commerce_tap_webhook(request: Request):
    if not COMMERCE_TEST or not verify_tap_hashstring:
        return utf8_json_response({"status": "unavailable"}, status_code=503)
    if not os.getenv("TAP_SECRET_KEY", "").strip():
        return utf8_json_response({"status": "unconfigured", "reason": "TAP_SECRET_KEY_missing"}, status_code=503)
    try:
        payload = await request.json()
    except Exception:
        return utf8_json_response({"status": "invalid", "reason": "invalid_json"}, status_code=400)
    received_hash = request.headers.get("hashstring") or request.headers.get("x-tap-hashstring") or ""
    if not verify_tap_hashstring(payload, received_hash):
        return utf8_json_response({"status": "rejected", "reason": "tap_hashstring_invalid"}, status_code=401)
    try:
        result = COMMERCE_TEST.process_payment_webhook(
            event_id=str(payload.get("id") or ""),
            order_id=str((payload.get("reference") or {}).get("order") or ""),
            event_type=str(payload.get("object") or "charge"),
            status=tap_status_to_test_status(str(payload.get("status") or "")),
            payload=payload,
            provider="tap_sandbox",
        )
    except (KeyError, ValueError) as exc:
        return utf8_json_response({"status": "invalid", "reason": str(exc)}, status_code=422)
    return utf8_json_response({"status": "verified", "tap": result})


@app.post('/test/commerce/orders/{order_id}/shipment')
async def test_commerce_create_shipment(order_id: str, payload: dict | None = None):
    if not COMMERCE_TEST:
        return utf8_json_response({"status": "unavailable"}, status_code=503)
    try:
        result = COMMERCE_TEST.create_test_shipment(order_id, provider=str((payload or {}).get("provider", "test_carrier")))
    except KeyError as exc:
        return utf8_json_response({"status": "not_found", "reason": str(exc)}, status_code=404)
    except ValueError as exc:
        return utf8_json_response({"status": "blocked", "reason": str(exc)}, status_code=409)
    return utf8_json_response(result)


@app.get('/test/commerce/orders/{order_id}/shipment')
async def test_commerce_get_shipment(order_id: str):
    if not COMMERCE_TEST:
        return utf8_json_response({"status": "unavailable"}, status_code=503)
    try:
        return utf8_json_response(COMMERCE_TEST.get_test_shipment(order_id))
    except KeyError as exc:
        return utf8_json_response({"status": "not_found", "reason": str(exc)}, status_code=404)


@app.post('/test/commerce/webhooks/shipping')
async def test_commerce_shipping_webhook(payload: dict):
    if not COMMERCE_TEST:
        return utf8_json_response({"status": "unavailable"}, status_code=503)
    required = ("event_id", "shipment_id", "status")
    missing = [key for key in required if not payload.get(key)]
    if missing:
        return utf8_json_response({"status": "invalid", "missing": missing}, status_code=422)
    try:
        result = COMMERCE_TEST.process_shipping_webhook(
            event_id=str(payload["event_id"]),
            shipment_id=str(payload["shipment_id"]),
            status=str(payload["status"]),
            payload=payload,
            provider=str(payload.get("provider", "test_carrier")),
        )
    except KeyError as exc:
        return utf8_json_response({"status": "not_found", "reason": str(exc)}, status_code=404)
    except ValueError as exc:
        return utf8_json_response({"status": "invalid", "reason": str(exc)}, status_code=422)
    return utf8_json_response(result)


@app.get('/gateway/status')
async def gateway_status():
    if not KERNEL or not getattr(KERNEL, "project_gateway", None):
        return utf8_json_response({"status": "unavailable"}, status_code=503)
    return utf8_json_response({"status": "ok", **KERNEL.project_gateway.snapshot()})


@app.post('/gateway/authorize')
async def gateway_authorize(payload: dict):
    if not KERNEL or not getattr(KERNEL, "project_gateway", None):
        return utf8_json_response({"status": "unavailable"}, status_code=503)
    required = ("subject_id", "role_id", "project_id", "capability")
    missing = [key for key in required if not payload.get(key)]
    if missing:
        return utf8_json_response({"status": "invalid", "missing": missing}, status_code=422)
    try:
        result = KERNEL.project_gateway.route_to_ameer(
            subject_id=str(payload["subject_id"]),
            role_id=str(payload["role_id"]),
            project_id=str(payload["project_id"]),
            capability=str(payload["capability"]),
            action=str(payload.get("action", "read")),
            context=payload.get("context") if isinstance(payload.get("context"), dict) else {},
            worker_id=payload.get("worker_id"),
        )
    except (TypeError, ValueError) as exc:
        return utf8_json_response({"status": "invalid", "reason": str(exc)}, status_code=422)
    return utf8_json_response(result, status_code=200 if result.get("allowed") else 403)


@app.get('/shadow/policies')
async def shadow_policies():
    """Read-only policy snapshot; never exposes credentials or prompts."""
    if not KERNEL or not getattr(KERNEL, "shadow_foundation", None):
        return utf8_json_response({"status": "unavailable"}, status_code=503)
    snapshot = KERNEL.shadow_foundation.snapshot()
    return utf8_json_response({"status": "ok", "policies": snapshot["policies"], "trading_execution_default": snapshot["trading_execution_default"]})


@app.get('/authority')
async def authority_snapshot():
    """Public, credential-free summary of Ameer's delegated operating authority."""
    return utf8_json_response({"status": "ok", "authority": authority_policy_snapshot()})


@app.get('/projects')
async def list_projects():
    return {"projects": _load_project_store()}


@app.post('/projects')
async def create_project(payload: ProjectRequest):
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Empty project name")
    projects = _load_project_store()
    existing = [p for p in projects if p.get("name", "").lower() == name.lower()]
    if existing:
        return {"created": False, "projects": projects}
    projects.append({"name": name, "description": payload.description or "", "created_at": datetime.now(timezone.utc).isoformat()})
    _save_project_store(projects)
    return {"created": True, "projects": projects}


@app.get('/', response_class=HTMLResponse)
async def home():
    try:
        with open(WEB_INDEX, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read(), media_type="text/html; charset=utf-8")
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Ameer</h1><p>Web UI not found. Create 09_Assets/web/index.html</p>", media_type="text/html; charset=utf-8")


@app.get('/kernel/health')
async def kernel_health():
    """حالة Ameer Operating System Kernel."""
    if not KERNEL:
        return utf8_json_response({"status": "unavailable", "kernel": "inactive"})
    return utf8_json_response(KERNEL.health())


@app.get('/kernel/workspace')
async def kernel_workspace():
    """ملخص بيئة العمل الحالي."""
    if not KERNEL:
        return utf8_json_response({"status": "unavailable"})
    summary = KERNEL.refresh_workspace()
    return utf8_json_response({"workspace_summary": summary})


@app.get('/decisions')
async def get_decisions():
    """آخر القرارات التنفيذية المسجّلة."""
    if not KERNEL:
        return utf8_json_response({"status": "unavailable", "decisions": []})
    return utf8_json_response(KERNEL.decisions.snapshot())


@app.post('/decisions')
async def post_decision(request: Request):
    """تسجيل قرار تنفيذي جديد."""
    if not KERNEL:
        return utf8_json_response({"status": "unavailable"}, status_code=503)
    try:
        body = await request.json()
    except Exception:
        return utf8_json_response({"error": "invalid JSON"}, status_code=400)
    title = (body.get("title") or "").strip()
    reason = (body.get("reason") or "").strip()
    if not title or not reason:
        return utf8_json_response({"error": "title and reason are required"}, status_code=400)
    decision_id = KERNEL.record_decision(
        title=title,
        reason=reason,
        category=body.get("category", "other"),
        expected_outcome=body.get("expected_outcome", ""),
    )
    return utf8_json_response({"id": decision_id, "status": "recorded"})


@app.get('/approvals')
async def get_approvals():
    """طلبات الموافقة المعلّقة."""
    if not KERNEL:
        return utf8_json_response({"status": "unavailable", "approvals": []})
    return utf8_json_response(KERNEL.approvals.snapshot())


@app.post('/approvals')
async def post_approval_request(request: Request):
    """طلب موافقة المؤسسة على إجراء حساس."""
    if not KERNEL:
        return utf8_json_response({"status": "unavailable"}, status_code=503)
    try:
        body = await request.json()
    except Exception:
        return utf8_json_response({"error": "invalid JSON"}, status_code=400)
    action = (body.get("action") or "other").strip()
    description = (body.get("description") or "").strip()
    if not description:
        return utf8_json_response({"error": "description is required"}, status_code=400)
    approval_id = KERNEL.request_approval(
        action=action,
        description=description,
        requested_by=body.get("requested_by", "executive_brain"),
    )
    return utf8_json_response({"id": approval_id, "status": "pending"})


@app.post('/approvals/{approval_id}/approve')
async def approve_request(approval_id: str, request: Request):
    """موافقة المؤسسة على طلب."""
    if not KERNEL:
        return utf8_json_response({"status": "unavailable"}, status_code=503)
    try:
        body = await request.json()
    except Exception:
        body = {}
    approved_by = body.get("approved_by", "naseem")
    updated = KERNEL.approvals.approve(approval_id, approved_by=approved_by)
    if not updated:
        return utf8_json_response({"error": "approval not found or already resolved"}, status_code=404)
    governance_result = KERNEL.memory_governance.finalize_approval(approval_id, approved_by=approved_by)
    return utf8_json_response(
        {"id": approval_id, "status": "approved", "memory_governance": governance_result}
    )


@app.post('/approvals/{approval_id}/reject')
async def reject_request(approval_id: str, request: Request):
    """رفض المؤسسة لطلب."""
    if not KERNEL:
        return utf8_json_response({"status": "unavailable"}, status_code=503)
    try:
        body = await request.json()
        reason = body.get("reason", "")
        rejected_by = body.get("rejected_by", "naseem")
    except Exception:
        reason = ""
        rejected_by = "naseem"
    updated = KERNEL.approvals.reject(approval_id, reason=reason, rejected_by=rejected_by)
    if not updated:
        return utf8_json_response({"error": "approval not found or already resolved"}, status_code=404)
    discard_result = KERNEL.memory_governance.discard_candidate(
        approval_id,
        rejected_by=rejected_by,
        reason=reason,
    )
    return utf8_json_response(
        {"id": approval_id, "status": "rejected", "memory_governance": discard_result}
    )


@app.post('/feedback')
async def post_feedback(request: Request):
    """تسجيل تغذية راجعة من المؤسسة."""
    if not KERNEL:
        return utf8_json_response({"status": "unavailable"}, status_code=503)
    try:
        body = await request.json()
    except Exception:
        return utf8_json_response({"error": "invalid JSON"}, status_code=400)
    feedback_type = body.get("feedback_type", "")
    topic = body.get("topic", "")
    comment = body.get("comment", "")
    context = body.get("context") or {}
    source = body.get("source", "founder")
    try:
        fid = KERNEL.feedback.record(
            feedback_type=feedback_type,
            topic=topic,
            comment=comment,
            context=context,
            source=source,
        )
    except ValueError as exc:
        return utf8_json_response({"error": "invalid promotion request"}, status_code=422)
    return utf8_json_response({"id": fid, "status": "recorded"})


@app.get('/feedback')
async def get_feedback():
    """استرجاع سجل التغذية الراجعة."""
    if not KERNEL:
        return utf8_json_response({"status": "unavailable"}, status_code=503)
    return utf8_json_response({"feedback": KERNEL.feedback.recent(50), "snapshot": KERNEL.feedback.snapshot()})


@app.get('/learning/preferences')
async def get_learning_preferences():
    """استرجاع التفضيلات المُتعلَّمة وتشغيل دورة تعلم."""
    if not KERNEL:
        return utf8_json_response({"status": "unavailable"}, status_code=503)
    cycle_result = KERNEL.learning.run_learning_cycle()
    return utf8_json_response({
        "preferences": KERNEL.learning.get_preferences(),
        "learning_snapshot": KERNEL.learning.snapshot(),
        "last_cycle": cycle_result,
    })


@app.post('/execute')
async def execute_tasks(request: Request):
    """
    POST /execute — تنفيذ مهام حقيقية عبر Pipeline الكامل.

    يُوصل مباشرةً بـ:
        ExecutiveKernel → PlanValidator → Scheduler → FileExecutor

    طلب مثال:
        POST /execute
        {
          "tasks": [
            {
              "id": "home-index",
              "action": "write",
              "executor": "file",
              "target": "09_Assets/runtime_workspace/home/index.html",
              "content": "<!DOCTYPE html>...",
              "priority": "high"
            }
          ]
        }

    الاستجابة:
        {
          "accepted": true,
          "validation": { ... },
          "schedule": { ... },
          "execution": {
            "completed": 1,
            "failed": 0,
            "blocked": 0,
            "results": [ { "task_id": "home-index", "status": "completed", ... } ]
          },
          "tasks_queued": 1
        }

    قيود الأمان:
        - كل الأهداف يجب أن تقع داخل 09_Assets/runtime_workspace
        - الكتابة خارج هذا المسار مرفوضة تلقائياً من PlanValidator
    """
    if not KERNEL:
        return utf8_json_response({"status": "unavailable", "kernel": "inactive"}, status_code=503)

    try:
        body = await request.json()
    except Exception:
        return utf8_json_response({"error": "invalid JSON"}, status_code=400)

    tasks = body.get("tasks")
    if not isinstance(tasks, list) or len(tasks) == 0:
        return utf8_json_response(
            {"error": "tasks field is required and must be a non-empty list"},
            status_code=422,
        )

    _guardian_for_execute: dict = body.get("guardian") or {}
    _task_actions = {str(t.get("action", "")).strip().lower() for t in tasks if isinstance(t, dict)}
    _high_risk_actions = {"delete", "publish", "external", "financial"}
    _action_priority = ["financial", "delete", "publish", "external"]
    if _task_actions & _high_risk_actions:
        _derived_action = next(action for action in _action_priority if action in _task_actions)
    elif _task_actions - {"", "write"}:
        _derived_action = next(action for action in sorted(_task_actions) if action not in {"", "write"})
    elif "write" in _task_actions:
        _derived_action = "write"
    else:
        _log("execute_tasks_boundary_denied", reason="unknown_action")
        return utf8_json_response(
            {"accepted": False, "reason": "unknown_action"},
            status_code=422,
        )

    _exec_boundary = _boundary_for_server_execution()
    _exec_boundary_result = None
    _exec_boundary_allowed = False
    if _exec_boundary is not None:
        _exec_boundary_result = _exec_boundary.evaluate(
            guardian=_guardian_for_execute,
            request_type="execution",
            intent="execute_tasks",
            capability_name="file_operations",
            action=_derived_action,
            context={"task_count": len(tasks), "actions": list(_task_actions)},
            requested_by="execute_endpoint",
        )
        _exec_boundary_allowed = bool(getattr(_exec_boundary_result, "allowed", False))
    if not _exec_boundary_allowed:
        _deny_reason = getattr(_exec_boundary_result, "reason", "boundary_missing")
        _log("execute_tasks_boundary_denied", reason=_deny_reason)
        return utf8_json_response(
            {"accepted": False, "reason": _deny_reason},
            status_code=422,
        )

    try:
        # KERNEL.execute_task(tasks)
        report = KERNEL.execute_task(
            tasks,
            guardian=_guardian_for_execute,
            request_type="execution",
            intent="execute_tasks",
            requested_by="execute_endpoint",
        )
    except Exception as exc:
        _log("execute_task_error", level="error", error=str(exc))
        return utf8_json_response({"error": "execution failed — see server logs"}, status_code=500)

    status_code = 200 if report.get("accepted") else 422
    return utf8_json_response(report, status_code=status_code)


@app.post('/workers/probe')
async def workers_probe(request: Request):
    """Run a read-only model probe for one registered worker.

    This endpoint never invokes file, shell, browser, mail, deployment, or other
    external tools. It exists to prove worker adapter invocation separately from
    the side-effecting command pipeline. A valid Guardian probe scope is required.
    """
    if not KERNEL or not getattr(KERNEL, "worker_runtime", None):
        return utf8_json_response({"status": "unavailable", "reason": "worker_runtime_unavailable"}, status_code=503)
    try:
        body = await request.json()
    except Exception:
        return utf8_json_response({"status": "invalid_request", "reason": "invalid_json"}, status_code=400)
    guardian = body.get("guardian") or {}
    if guardian.get("status") != "pass" or guardian.get("scope") != "worker_probe_read_only":
        return utf8_json_response({
            "status": "blocked",
            "reason": "guardian_not_pass",
            "required": {"status": "pass", "scope": "worker_probe_read_only"},
        }, status_code=422)
    worker_id = str(body.get("worker_id", "")).strip().lower()
    objective = str(body.get("objective", "")).strip()
    if not worker_id or not objective:
        return utf8_json_response({"status": "invalid_request", "reason": "worker_id_and_objective_required"}, status_code=422)
    if len(objective) > 500:
        return utf8_json_response({"status": "invalid_request", "reason": "objective_too_long"}, status_code=422)
    if _probe_has_non_negated_forbidden_term(objective):
        return utf8_json_response({"status": "blocked", "reason": "external_or_side_effecting_objective"}, status_code=422)
    started = datetime.now(timezone.utc)
    result = KERNEL.worker_runtime.dispatch(
        worker_id,
        objective,
        {"mode": "read_only_probe", "tools": [], "approval_required": False},
    )
    elapsed_ms = round((datetime.now(timezone.utc) - started).total_seconds() * 1000, 2)
    result["latency_ms"] = elapsed_ms
    result["probe"] = {"read_only": True, "tools": [], "external_effect": False}
    return utf8_json_response(result, status_code=200 if result.get("status") == "completed" else 422)


@app.post('/execute/command')
async def execute_command(request: Request):
    """
    POST /execute/command — تحويل أمر بشري إلى Task Batch وتنفيذه.

    المسار الكامل:
        human_command
            ↓ ExecutiveBrain
            ↓ TaskDecomposer
            ↓ PlanValidator
            ↓ Scheduler
            ↓ FileExecutor
            ↓ files created

    طلب مثال:
        POST /execute/command
        { "command": "ابنِ الصفحة الرئيسية" }

    الاستجابة: trace كامل لكل خطوة في الـ Pipeline.
    """
    if not KERNEL:
        return utf8_json_response({"status": "unavailable", "kernel": "inactive"}, status_code=503)

    try:
        body = await request.json()
    except Exception:
        return utf8_json_response({"error": "invalid JSON"}, status_code=400)

    command = str(body.get("command", "")).strip()
    if not command:
        return utf8_json_response({"error": "command field is required"}, status_code=422)

    _cmd_guardian: dict = body.get("guardian") or {}
    _cmd_intent = "unknown"
    _cmd_action = "write"
    try:
        _cmd_decomposition = KERNEL.task_decomposer.decompose(command)
        _cmd_intent = str(_cmd_decomposition.get("intent", "unknown") or "unknown").strip().lower()
        _cmd_first_task = (_cmd_decomposition.get("tasks") or [{}])[0]
        _cmd_action = str(_cmd_first_task.get("action", "write") or "write").strip().lower() or "write"
    except Exception:
        pass

    _cmd_boundary = _boundary_for_server_execution()
    _cmd_boundary_result = None
    _cmd_boundary_allowed = False
    if _cmd_boundary is not None:
        _cmd_boundary_result = _cmd_boundary.evaluate(
            guardian=_cmd_guardian,
            request_type="execution",
            intent=_cmd_intent,
            capability_name="file_operations",
            action=_cmd_action,
            context={"command": command[:240]},
            requested_by="execute_command_endpoint",
        )
        _cmd_boundary_allowed = bool(getattr(_cmd_boundary_result, "allowed", False))
    if not _cmd_boundary_allowed:
        _cmd_deny_reason = getattr(_cmd_boundary_result, "reason", "boundary_missing")
        _log("execute_command_boundary_denied", reason=_cmd_deny_reason, command=command[:120])
        return utf8_json_response(
            {"accepted": False, "reason": _cmd_deny_reason},
            status_code=422,
        )

    try:
        # KERNEL.execute_command(command)
        trace = KERNEL.execute_command(
            command,
            guardian=_cmd_guardian,
            request_type="execution",
            requested_by="execute_command_endpoint",
        )
    except Exception as exc:
        _log("execute_command_error", level="error", command=command, error=str(exc))
        return utf8_json_response({"error": "execution failed — see server logs"}, status_code=500)

    accepted = trace.get("final", {}).get("accepted", False)
    _log(
        "execute_command_completed",
        command=command,
        intent=trace.get("pipeline", [{}])[0].get("output", {}).get("intent"),
        accepted=accepted,
        completed=trace.get("final", {}).get("completed", 0),
    )
    return utf8_json_response(trace, status_code=200 if accepted else 422)


@app.get('/preview', response_class=HTMLResponse)
async def preview_home():
    """
    GET /preview — عرض الصفحة الرئيسية المُنشأة بواسطة أمير.

    تُخدَم من 09_Assets/runtime_workspace/home/index.html.
    """
    preview_path = os.path.join(ROOT, "09_Assets", "runtime_workspace", "home", "index.html")
    if not os.path.exists(preview_path):
        return HTMLResponse(
            content=(
                "<html lang='ar' dir='rtl'><head><meta charset='utf-8'>"
                "<title>Preview</title></head><body style='font-family:sans-serif;padding:2rem;'>"
                "<h2>لم يتم إنشاء الصفحة الرئيسية بعد.</h2>"
                "<p>أرسل الأمر: <code>ابنِ الصفحة الرئيسية</code> عبر <code>POST /execute/command</code> أولاً.</p>"
                "</body></html>"
            ),
            media_type="text/html; charset=utf-8",
            status_code=404,
        )
    with open(preview_path, "r", encoding="utf-8") as f:
        content = f.read()
    # Inline CSS and JS so the preview works without a static file server
    css_path = os.path.join(ROOT, "09_Assets", "runtime_workspace", "home", "style.css")
    js_path = os.path.join(ROOT, "09_Assets", "runtime_workspace", "home", "script.js")
    if os.path.exists(css_path):
        css = open(css_path, encoding="utf-8").read()
        content = content.replace('<link rel="stylesheet" href="style.css" />', f"<style>{css}</style>")
    if os.path.exists(js_path):
        js = open(js_path, encoding="utf-8").read()
        content = content.replace('<script src="script.js"></script>', f"<script>{js}</script>")
    return HTMLResponse(content=content, media_type="text/html; charset=utf-8")


PROJECT_ACTION_BAR = r'''
<style>
.ameer-project-actions{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Tahoma,Arial,sans-serif;max-width:1120px;margin:22px auto;padding:17px;background:#ffffffef;border:1px solid #e2e9f5;border-radius:22px;box-shadow:0 16px 38px rgba(23,35,67,.12);direction:rtl;position:relative;z-index:5}.ameer-project-actions .bar-head{display:flex;align-items:center;justify-content:space-between;gap:14px}.ameer-project-actions .bar-kicker{display:inline-flex;align-items:center;gap:6px;color:#315ed2;font-size:11px;font-weight:900}.ameer-project-actions .bar-head strong{display:block;margin-top:4px;color:#14213b;font-size:18px}.ameer-project-actions .bar-head small{color:#72809a;font-size:12px;line-height:1.6}.ameer-project-actions .bar-form{display:grid;grid-template-columns:1fr auto;gap:8px;margin-top:14px}.ameer-project-actions input{min-width:0;border:1px solid #d7e0f1;border-radius:12px;padding:11px 12px;background:#f8faff;color:#172033;font:inherit}.ameer-project-actions button,.ameer-project-actions a{border:0;border-radius:12px;padding:10px 13px;font:inherit;font-weight:850;cursor:pointer;text-decoration:none}.ameer-project-actions .run{background:#3467e8;color:#fff}.ameer-project-actions .links{display:flex;flex-wrap:wrap;gap:7px;margin-top:10px}.ameer-project-actions .link{background:#edf2ff;color:#315ed2;border:1px solid #cbd9ff}.ameer-project-actions .link.personal{background:#f3efff;color:#6845ba;border-color:#ded2ff}.ameer-project-actions .status{min-height:18px;margin-top:9px;color:#72809a;font-size:12px}.ameer-project-actions .status.ok{color:#13865a}@media(max-width:700px){.ameer-project-actions .bar-head{align-items:flex-start;flex-direction:column}.ameer-project-actions .bar-form{grid-template-columns:1fr}.ameer-project-actions .links>*{flex:1;text-align:center}}
</style>
<section class="ameer-project-actions" data-project-slug="__PROJECT_SLUG__">
  <div class="bar-head"><div><span class="bar-kicker">● مشروع تحت إدارة أمير</span><strong>استمر في بناء هذا الموقع من غرفة القيادة</strong></div><small>اكتب تعديلك، ثم يفتح أمير محادثة الأعمال بالسياق الصحيح. الحذف والنشر لا يطلبان قرارًا إلا من بطاقة المحادثة.</small></div>
  <div class="bar-form"><input data-project-objective placeholder="مثال: حسّن صفحة الأسعار واختبرها" aria-label="مهمة المشروع"><button class="run" data-project-send type="button">متابعة مع أمير ←</button></div>
  <div class="links"><a class="link" data-project-business href="/#business">محادثة الأعمال</a><a class="link personal" href="/#personal">المحادثة الشخصية</a><a class="link" href="/#activity">سجل التنفيذ</a></div>
  <div class="status" data-project-status>هذه المعاينة جزء من مشروع أمير. لا يوجد تنفيذ أو نشر مخفي في هذه الصفحة.</div>
</section>
<script>
(function(){
 const bar=document.querySelector('.ameer-project-actions'); if(!bar) return;
 const slug=bar.dataset.projectSlug, input=bar.querySelector('[data-project-objective]'), status=bar.querySelector('[data-project-status]');
 const handoff=()=>{const detail=input.value.trim()||'راجع المشروع واقترح التحسين الأعلى أثرًا ثم نفّذه واختبره';const task='ضمن مشروع '+slug+': '+detail;status.textContent='يتم فتح محادثة الأعمال بهذه المهمة…';window.location.href='/?intent='+encodeURIComponent(task)+'#business';};
 bar.querySelector('[data-project-send]').onclick=handoff;
 bar.querySelector('[data-project-business]').onclick=event=>{event.preventDefault();handoff();};
})();
</script>
'''

@app.get('/preview/projects/{slug}', response_class=HTMLResponse)
async def preview_project(slug: str):
    """
    GET /preview/projects/{slug} — عرض مشروع عام مُنشأ بواسطة build_generic.

    يُخدَم من 09_Assets/runtime_workspace/projects/{slug}/index.html.
    """
    # Reject slugs that try to escape the projects directory
    if ".." in slug or "/" in slug or "\\" in slug:
        return HTMLResponse(
            content=(
                "<html lang='ar' dir='rtl'><head><meta charset='utf-8'>"
                "<title>خطأ</title></head><body style='font-family:sans-serif;padding:2rem;'>"
                "<h2>معرّف المشروع غير صالح.</h2>"
                "</body></html>"
            ),
            media_type="text/html; charset=utf-8",
            status_code=400,
        )

    project_dir = os.path.join(ROOT, "09_Assets", "runtime_workspace", "projects", slug)
    index_path = os.path.join(project_dir, "index.html")

    if not os.path.exists(index_path):
        return HTMLResponse(
            content=(
                f"<html lang='ar' dir='rtl'><head><meta charset='utf-8'>"
                f"<title>Preview</title></head><body style='font-family:sans-serif;padding:2rem;'>"
                f"<h2>لم يتم إنشاء المشروع بعد.</h2>"
                f"<p>المشروع <code>{slug}</code> غير موجود.</p>"
                f"</body></html>"
            ),
            media_type="text/html; charset=utf-8",
            status_code=404,
        )

    with open(index_path, "r", encoding="utf-8") as f:
        content = f.read()

    css_path = os.path.join(project_dir, "style.css")
    js_path = os.path.join(project_dir, "script.js")
    if os.path.exists(css_path):
        css = open(css_path, encoding="utf-8").read()
        content = content.replace('<link rel="stylesheet" href="style.css" />', f"<style>{css}</style>")
    if os.path.exists(js_path):
        js = open(js_path, encoding="utf-8").read()
        content = content.replace('<script src="script.js"></script>', f"<script>{js}</script>")

    safe_slug = html.escape(slug, quote=True)
    action_bar = PROJECT_ACTION_BAR.replace("__PROJECT_SLUG__", safe_slug)
    if "</body>" in content:
        content = content.replace("</body>", action_bar + "</body>")
    else:
        content += action_bar
    return HTMLResponse(content=content, media_type="text/html; charset=utf-8")


@app.post('/learning/reset')
async def reset_learning():
    """إعادة ضبط التفضيلات المُتعلَّمة إلى الإعدادات الافتراضية (بموافقة المؤسسة)."""
    if not KERNEL:
        return utf8_json_response({"status": "unavailable"}, status_code=503)
    KERNEL.learning.reset_preferences()
    return utf8_json_response({"status": "reset", "preferences": KERNEL.learning.get_preferences()})


@app.on_event("startup")
async def log_runtime_banner():
    meta = runtime_metadata(workspace_root=REPO_ROOT)
    _log(
        "runtime_started",
        build=meta["build"],
        commit=meta["commit"],
        host=meta["host"],
        port=meta["port"],
        pid=meta["pid"],
        started_at=meta["started_at"],
        documents=len(DOCUMENTS),
    )
    # Boot the Executive Operating Kernel
    if KERNEL:
        try:
            boot_result = KERNEL.boot()
            _log(
                "aos_kernel_booted",
                status=boot_result.get("status"),
                components=boot_result.get("components"),
                errors=boot_result.get("errors"),
            )
        except Exception as exc:
            _log("aos_kernel_boot_failed", level="error", error=str(exc))

if __name__ == '__main__':
    import uvicorn
    os.environ.setdefault("AMEER_PORT", str(resolve_port()))
    uvicorn.run('ameer_server:app', host=resolve_host(), port=resolve_port(), reload=False)
