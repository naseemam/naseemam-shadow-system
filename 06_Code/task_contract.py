"""
task_contract.py
================
P1.2 Task contract builder for Executive Runtime.

This module converts an execution request into concrete task objects that
follow the frozen P1 runtime contract and target the sandbox workspace.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict


TASK_SCHEMA_VERSION = 1
RUNTIME_SANDBOX_ROOT = "09_Assets/runtime_workspace"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "generated-page"


def _extract_page_name(query: str) -> str:
    text = (query or "").strip()
    lowered = text.lower()

    if any(token in lowered for token in ["home", "homepage", "الرئيسية", "الصفحه الرئيسيه", "الصفحة الرئيسية"]):
        return "home"

    match = re.search(
        r"(?:page|صفحة|صفحه)(?:\s+named|\s+باسم|\s+اسمها|\s+اسم)?\s+[\"']?([\u0600-\u06FFA-Za-z0-9 _-]+)[\"']?",
        text,
        flags=re.IGNORECASE,
    )
    if match:
        raw = match.group(1).strip()
        raw = re.split(r"\s+(?:html|داخل|in|with|تحتوي|contains)\b", raw, maxsplit=1, flags=re.IGNORECASE)[0].strip()
        return _slugify(raw)

    return "generated-page"


def _default_html(page_name: str, title: str) -> str:
    return (
        "<!doctype html>\n"
        "<html lang=\"ar\">\n"
        "  <head>\n"
        "    <meta charset=\"utf-8\">\n"
        "    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
        f"    <title>{title}</title>\n"
        "  </head>\n"
        "  <body>\n"
        f"    <main data-page=\"{page_name}\">\n"
        f"      <h1>{title}</h1>\n"
        "      <p>Generated inside runtime workspace sandbox.</p>\n"
        "    </main>\n"
        "  </body>\n"
        "</html>\n"
    )


def build_task_object(query: str, plan: Any | None = None) -> Dict[str, Any]:
    page_name = _extract_page_name(query)
    title = "Home" if page_name == "home" else page_name.replace("-", " ").title()
    approval_required = bool(getattr(plan, "guardian_status", "pass") != "pass")
    task_id = f"task-{uuid.uuid4().hex[:8]}"

    return {
        "schema_version": TASK_SCHEMA_VERSION,
        "id": task_id,
        "action": "create_file",
        "target": f"{RUNTIME_SANDBOX_ROOT}/{page_name}/index.html",
        "executor": "file",
        "inputs": {
            "content": _default_html(page_name, title),
        },
        "approval_required": approval_required,
        "dependencies": [],
        "priority": 50,
        "metadata": {
            "source": "task_decomposer",
            "created_at": _now(),
            "request_query": (query or "").strip(),
            "request_type": getattr(plan, "request_type", "execution") or "execution",
            "sandboxed": True,
        },
    }


def build_execution_task_batch(query: str, plan: Any | None = None) -> Dict[str, Any]:
    task = build_task_object(query, plan=plan)
    return {
        "run_id": f"run-{uuid.uuid4().hex[:10]}",
        "goal": (query or "").strip(),
        "task_count": 1,
        "tasks": [task],
        "sandbox_root": RUNTIME_SANDBOX_ROOT,
    }