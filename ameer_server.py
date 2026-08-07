from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
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

# Load markdown documents from workspace (always from the repo checkout)
ROOT = DATA_ROOT
MODULES_DIR = os.path.join(REPO_ROOT, "09_Assets", "web", "modules")
app.mount("/modules", StaticFiles(directory=MODULES_DIR), name="modules")
MD_GLOB = os.path.join(REPO_ROOT, "**", "*.md")
WEB_INDEX = os.path.join(REPO_ROOT, "09_Assets", "web", "index.html")
DEBUG_MODE = os.getenv("AMEER_DEBUG", "0").lower() in {"1", "true", "yes", "on"}
RUNTIME_METADATA = runtime_metadata(workspace_root=REPO_ROOT)

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
    if isinstance(value, dict):
        clean = {}
        for k, v in value.items():
            key = str(k).lower()
            if "traceback" in key or "stack" in key:
                continue
            clean[k] = _sanitize_response_payload(v)
        return clean
    if isinstance(value, list):
        return [_sanitize_response_payload(v) for v in value]
    return value


def utf8_json_response(payload, headers: dict[str, str] | None = None, status_code: int = 200):
    safe_payload = _sanitize_response_payload(payload)
    return JSONResponse(content=safe_payload, headers=headers or {}, status_code=status_code)


DOCUMENTS = load_documents()

class AskRequest(BaseModel):
    query: str = ""
    message: str = ""
    max_results: int = 5

    @property
    def resolved_query(self) -> str:
        return (self.query or self.message).strip()

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
    q = req.resolved_query
    if not q:
        raise HTTPException(status_code=400, detail="Empty query")

    _log("ask_received", request_id=request_id, build_id=RUNTIME_METADATA["build_id"])

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

    # ── 3. Executive Brain think + execute ────────────────────────────────────
    plan = EXECUTIVE_BRAIN.think(
        q,
        DOCUMENTS,
        guardian_result=guardian,
        routing_hint=routing,
    )
    # P0.2 — pass existing plan so get_reasoning_output does NOT call think() again
    reasoning_output = EXECUTIVE_BRAIN.get_reasoning_output(
        q,
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
    kernel_execution_trace: dict | None = None
    kernel_execution_reply: str | None = None
    if KERNEL:
        try:
            decomp = KERNEL.task_decomposer.decompose(q)
            if decomp.get("intent", "unknown") != "unknown":
                kernel_execution_trace = KERNEL.execute_command(q)
                final_exec = kernel_execution_trace.get("final", {})
                if final_exec.get("accepted"):
                    completed = final_exec.get("completed", 0)
                    files = final_exec.get("files_created") or []
                    file_list = "، ".join(f for f in files if f) if files else ""
                    _exec_intent = kernel_execution_trace.get("pipeline", [{}])[0].get("output", {}).get("intent", "")
                    _preview_hint = ""
                    _pp = final_exec.get("preview_path") or ""
                    if "/projects/" in _pp:
                        _slug = _pp.split("/projects/", 1)[1].replace("/index.html", "").rstrip("/")
                        _preview_hint = f"\n\nيمكنك معاينة الصفحة الآن عبر: /preview/projects/{_slug}"
                    elif _pp.endswith("home/index.html"):
                        _preview_hint = "\n\nيمكنك معاينتها الآن عبر رابط Preview أدناه."
                    _page_label = "الصفحة الرئيسية" if _exec_intent == "build_homepage" else "الصفحة"
                    kernel_execution_reply = (
                        f"✅ تم بناء {_page_label} بنجاح! "
                        f"أُنشئت {completed} ملفات"
                        + (f": {file_list}" if file_list else "")
                        + "."
                        + _preview_hint
                    )
                elif not final_exec.get("accepted") and kernel_execution_trace.get("pipeline"):
                    kernel_execution_reply = (
                        "⚠️ لم يتمكن أمير من إتمام التنفيذ. "
                        "راجع خطوات Pipeline أدناه لمعرفة سبب التوقف."
                    )
        except Exception:
            pass
    # ── 4. Compose fallback reply (used only if ECE is unavailable) ─────────────
    fallback_reply, reply_source = EXECUTIVE_BRAIN.compose_final_reply(
        q,
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
            q,
            active_projects=active_projects,
            running_tasks=running_tasks,
            pending_approvals=pending_approvals,
            workspace_summary=workspace_summary,
            executive_assessment=executive_assessment,
        )
        conversation_result = EXECUTIVE_CONVERSATION_ENGINE.execute(
            query=q,
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

    # ── 5b. Override reply when kernel execution succeeded ────────────────────
    if kernel_execution_reply is not None:
        final_reply = kernel_execution_reply
        reply_source = "executive_kernel"

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
    user_payload.update(public_runtime_identity(workspace_root=REPO_ROOT))
    user_payload["request_id"] = request_id
    if kernel_execution_trace is not None:
        user_payload["execution_trace"] = kernel_execution_trace
        _preview_path = kernel_execution_trace.get("final", {}).get("preview_path") or ""
        if _preview_path:
            # Derive preview URL from preview_path
            # e.g. "09_Assets/runtime_workspace/projects/حلم-الندى/index.html"
            # → "/preview/projects/حلم-الندى"
            if "/projects/" in _preview_path:
                _slug = _preview_path.split("/projects/", 1)[1].replace("/index.html", "").rstrip("/")
                user_payload["preview_url"] = f"/preview/projects/{_slug}"
            elif _preview_path.endswith("home/index.html"):
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
    q = req.resolved_query
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
        "started_at": meta["started_at"],
        "documents": len(DOCUMENTS),
        "ameer_status": {
            "Server": "Online",
            "Documents": "Ready",
            "Brain": "Ready",
            "Memory": "Ready",
            "Projects": "Ready",
        },
    }
    return utf8_json_response(payload, headers=runtime_headers(workspace_root=REPO_ROOT))


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

    try:
        report = KERNEL.execute_task(tasks)
    except Exception as exc:
        _log("execute_task_error", level="error", error=str(exc))
        return utf8_json_response({"error": "execution failed — see server logs"}, status_code=500)

    status_code = 200 if report.get("accepted") else 422
    return utf8_json_response(report, status_code=status_code)


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

    try:
        trace = KERNEL.execute_command(command)
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
    home_dir = os.path.join(ROOT, "09_Assets", "runtime_workspace", "home")
    content = _inline_assets(content, home_dir)
    return HTMLResponse(content=content, media_type="text/html; charset=utf-8")


def _inline_assets(html: str, base_dir: str) -> str:
    """Inline style.css and script.js into an HTML string so it renders without a file server.

    base_dir MUST already be validated / realpath-resolved by the caller.
    Only files that are direct children of base_dir (no sub-paths) are opened.
    """
    base_real = os.path.realpath(base_dir)

    def _safe_read(filename: str) -> str | None:
        target = os.path.realpath(os.path.join(base_real, filename))
        if not target.startswith(base_real + os.sep):
            return None
        if not os.path.isfile(target):
            return None
        with open(target, encoding="utf-8") as fh:
            return fh.read()

    css = _safe_read("style.css")
    if css is not None:
        html = html.replace('<link rel="stylesheet" href="style.css" />', f"<style>{css}</style>")
    js = _safe_read("script.js")
    if js is not None:
        html = html.replace('<script src="script.js"></script>', f"<script>{js}</script>")
    return html


@app.get('/preview/projects/{project_id:path}', response_class=HTMLResponse)
async def preview_project(project_id: str):
    """
    GET /preview/projects/{project_id} — عرض صفحة مشروع مُنشأة بواسطة أمير.

    تُخدَم من 09_Assets/runtime_workspace/projects/{project_id}/index.html.
    """
    import html as _html_mod
    projects_root = os.path.realpath(os.path.join(ROOT, "09_Assets", "runtime_workspace", "projects"))
    project_dir = os.path.realpath(os.path.join(projects_root, project_id))
    # Guard against path traversal — project_dir must be a strict child of projects_root
    if not project_dir.startswith(projects_root + os.sep):
        raise HTTPException(status_code=400, detail="Invalid project_id")
    preview_path = os.path.join(project_dir, "index.html")
    if not os.path.isfile(preview_path):
        safe_id = _html_mod.escape(project_id)
        return HTMLResponse(
            content=(
                "<html lang='ar' dir='rtl'><head><meta charset='utf-8'>"
                "<title>Preview</title></head><body style='font-family:sans-serif;padding:2rem;'>"
                f"<h2>لم يتم إنشاء المشروع «{safe_id}» بعد.</h2>"
                "<p>أرسل الأمر عبر <code>POST /ask</code> أولاً.</p>"
                "</body></html>"
            ),
            media_type="text/html; charset=utf-8",
            status_code=404,
        )
    with open(preview_path, "r", encoding="utf-8") as f:
        content = f.read()
    content = _inline_assets(content, project_dir)
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
