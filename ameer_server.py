from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import glob
import json
import logging
import os
import re
import sys
import uuid
import importlib.util
from datetime import datetime, timezone

from ameer_runtime import (
    public_runtime_identity,
    print_runtime_banner,
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
    getattr(_logger, level, _logger.info)(json.dumps(record, ensure_ascii=False))


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


AmeerOrchestrator = load_orchestrator_class()
ExecutiveBrainClass = load_executive_brain()
ResponseFormatterClass = load_response_formatter()

app = FastAPI(title="Ameer Local Server")


# Load markdown documents from workspace
ROOT = os.path.dirname(__file__)
MODULES_DIR = os.path.join(ROOT, "09_Assets", "web", "modules")
app.mount("/modules", StaticFiles(directory=MODULES_DIR), name="modules")
MD_GLOB = os.path.join(ROOT, "**", "*.md")
WEB_INDEX = os.path.join(ROOT, "09_Assets", "web", "index.html")
DEBUG_MODE = os.getenv("AMEER_DEBUG", "0").lower() in {"1", "true", "yes", "on"}
RUNTIME_METADATA = runtime_metadata(workspace_root=ROOT)

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
            rel = os.path.relpath(path, ROOT).replace("\\", "/")
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


def utf8_json_response(payload, headers: dict[str, str] | None = None):
    body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    return Response(content=body, media_type="application/json; charset=utf-8", headers=headers or {})


DOCUMENTS = load_documents()

class AskRequest(BaseModel):
    query: str
    max_results: int = 5

    class Config:
        extra = 'allow'


class MemoryRequest(BaseModel):
    text: str


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

    _log("ask_received", request_id=request_id, build_id=RUNTIME_METADATA["build_id"])
    autonomy_plan = None
    autonomy_keywords = ["plan", "planning", "memory", "autonom", "workspace", "document", "tool", "improve", "self", "reason"]
    if any(keyword in q.lower() for keyword in autonomy_keywords):
        autonomy_plan = _record_autonomy_plan(q, "autonomy")

    # Run orchestrator (retrieval + guardian)
    orchestrator_result = ORCHESTRATOR.answer(q, req.max_results)

    if not EXECUTIVE_BRAIN:
        raise HTTPException(status_code=500, detail="Executive Brain is unavailable")

    guardian = orchestrator_result.get("guardian", {})
    routing = orchestrator_result.get("routing") or {}
    project_manager = _manage_project_context(q)
    plan = EXECUTIVE_BRAIN.think(
        q,
        DOCUMENTS,
        guardian_result=guardian,
        routing_hint=routing,
    )
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
    final_reply, reply_source = EXECUTIVE_BRAIN.compose_final_reply(
        q,
        orchestrator_result,
        DOCUMENTS,
        existing_plan=plan,
        execution_result=execution_result,
    )

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
            "reply": "حاضر، تمت معالجة طلبك. إذا أردت تفاصيل إضافية أخبرني.",
            "message": "حاضر، تمت معالجة طلبك. إذا أردت تفاصيل إضافية أخبرني.",
            "assistant": "أمير",
        }
    user_payload.update(public_runtime_identity(workspace_root=ROOT))
    user_payload["request_id"] = request_id
    _log("ask_completed", request_id=request_id)
    return utf8_json_response(user_payload, headers=runtime_headers(workspace_root=ROOT))

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
    meta = runtime_metadata(workspace_root=ROOT)
    payload = {
        "status": meta["status"],
        "build": meta["build"],
        "build_id": meta["build_id"],
        "commit": meta["commit"],
        "host": meta["host"],
        "port": meta["port"],
        "workspace": meta["workspace"],
        "started_at": meta["started_at"],
        "pid": meta["pid"],
        "entrypoint": meta["entrypoint"],
        "documents": len(DOCUMENTS),
        "ameer_status": {
            "Server": "Online",
            "Documents": "Ready",
            "Brain": "Ready",
            "Memory": "Ready",
            "Projects": "Ready",
        },
    }
    return utf8_json_response(payload, headers=runtime_headers(workspace_root=ROOT))


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
    memory_file = os.path.join(ROOT, "04_Memory", "Preferences.md")
    os.makedirs(os.path.dirname(memory_file), exist_ok=True)
    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Empty memory text")
    if not os.path.exists(memory_file):
        with open(memory_file, "w", encoding="utf-8") as handle:
            handle.write("# Preferences\n\n")
    with open(memory_file, "r", encoding="utf-8") as handle:
        content = handle.read()
    note = f"- {datetime.now(timezone.utc).strftime('%Y-%m-%d')} — {text}"
    if note in content:
        return {"saved": True, "updated": False, "note": note, "file": "04_Memory/Preferences.md"}
    if "## User Notes" not in content:
        content = content.rstrip() + "\n\n## User Notes\n"
    else:
        content = content.rstrip() + "\n"
    content += note + "\n"
    with open(memory_file, "w", encoding="utf-8") as handle:
        handle.write(content)
    refresh_documents()
    return {"saved": True, "updated": True, "note": note, "file": "04_Memory/Preferences.md"}


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


@app.on_event("startup")
async def log_runtime_banner():
    meta = runtime_metadata(workspace_root=ROOT)
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

if __name__ == '__main__':
    import uvicorn
    os.environ.setdefault("AMEER_PORT", str(resolve_port()))
    uvicorn.run('ameer_server:app', host=resolve_host(), port=resolve_port(), reload=False)
