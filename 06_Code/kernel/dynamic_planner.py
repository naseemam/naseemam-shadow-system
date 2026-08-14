"""
dynamic_planner.py
==================
DynamicPlanner — يولّد خطة تنفيذ منظمة لأي هدف باستخدام inference provider.

بدلًا من أنماط regex ثابتة، يستخدم المخطط نموذج اللغة لتوليد قائمة مهام
مخصصة لكل هدف، مما يتيح تنفيذ أي هدف لم يُبرمج مسبقًا.

المخرج القياسي:
{
  "goal_id": "...",
  "goal": "...",
  "success_criteria": [...],
  "assumptions": [...],
  "architecture": {...},
  "tasks": [
    {
      "id": "...",
      "description": "...",
      "tool": "file.create|file.read|file.update|shell.run",
      "inputs": {...},
      "dependencies": [...],
      "effect_scope": "local_workspace|external_effect",
      "verification": {...}
    }
  ]
}
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ── System prompt for plan generation ─────────────────────────────────────────

_PLAN_SYSTEM_PROMPT = """\
أنت مخطط تنفيذي لنظام أمير. مهمتك: تحويل هدف عالي المستوى إلى خطة تنفيذ منظمة.

قواعد إلزامية:
1. أخرج JSON صالحًا فقط — بدون markdown أو شرح خارج الـ JSON.
2. كل مسارات الملفات يجب أن تبدأ بـ: 09_Assets/runtime_workspace/projects/{goal_id}/
3. محتوى الملفات في "content_prompt" يصف ما يجب أن يحتويه الملف (سيُنشأ المحتوى لاحقًا).
4. مهام shell.run: أوامر محلية فقط (pytest، npm، pip، إلخ) — ممنوع git push أو نشر خارجي.
5. رتّب المهام حسب التبعيات (الأولى أولًا).
6. أي نشر خارجي أو git push: effect_scope = "external_effect".
7. جميع عمليات مساحة العمل المحلية: effect_scope = "local_workspace".

البنية المطلوبة (JSON):
{
  "goal_id": "<uuid_short>",
  "goal": "<الهدف_المُعاد_صياغته>",
  "success_criteria": ["<معيار_1>", "<معيار_2>"],
  "assumptions": ["<افتراض_1>"],
  "architecture": {"<مكوّن>": "<وصف>"},
  "tasks": [
    {
      "id": "<task_id>",
      "description": "<ما_تفعله_هذه_المهمة>",
      "tool": "file.create",
      "inputs": {
        "path": "09_Assets/runtime_workspace/projects/<goal_id>/<filename>",
        "content_prompt": "<وصف_دقيق_لما_يجب_أن_يحتويه_الملف>"
      },
      "dependencies": [],
      "effect_scope": "local_workspace",
      "verification": {"type": "file_exists", "value": "<path>"}
    }
  ]
}

أدوات المتاحة:
- file.create: إنشاء ملف جديد (inputs: path, content_prompt)
- file.read:   قراءة ملف موجود (inputs: path)
- file.update: تحديث ملف موجود (inputs: path, content_prompt)
- shell.run:   تشغيل أمر shell (inputs: command, cwd[اختياري])

أخرج JSON فقط.
"""

_CONTENT_SYSTEM_PROMPT = """\
أنت مولّد كود متخصص لنظام أمير.
مهمتك: توليد محتوى ملف كامل وجاهز للاستخدام بناءً على الوصف المقدم.

قواعد:
1. أخرج محتوى الملف فقط — بدون شرح أو markdown.
2. اكتب كودًا حقيقيًا وعاملًا، لا placeholders.
3. التزم باللغة/الإطار المحدد في الوصف.
4. أضف تعليقات مفيدة باللغة المناسبة.
5. لا تضف ```code blocks``` — أخرج المحتوى مباشرة.
"""

_EVALUATION_SYSTEM_PROMPT = """\
أنت مُقيِّم اكتمال الأهداف لنظام أمير.
بناءً على الهدف الأصلي ونتائج التنفيذ، حدد هل اكتمل الهدف.

أخرج JSON فقط:
{
  "complete": true|false,
  "confidence": 0.0-1.0,
  "criteria_met": ["<معيار>", ...],
  "criteria_missing": ["<معيار>", ...],
  "summary": "<ملخص_بالعربية>"
}
"""

_REPAIR_SYSTEM_PROMPT = """\
أنت مُصلح أخطاء لنظام أمير.
مهمتك: تحليل فشل مهمة وتوليد مهام إصلاح.

أخرج JSON فقط:
{
  "analysis": "<تحليل_سبب_الفشل>",
  "repair_tasks": [
    {
      "id": "<repair_task_id>",
      "description": "<ما_تفعله>",
      "tool": "file.create|file.update|shell.run",
      "inputs": {...},
      "dependencies": [],
      "effect_scope": "local_workspace",
      "verification": {}
    }
  ]
}
"""


class DynamicPlanner:
    """
    مخطط ديناميكي يستخدم inference provider لتوليد خطة تنفيذ لأي هدف.

    الاستخدام:
    ----------
    planner = DynamicPlanner(providers=brain._providers, workspace_root=ROOT)
    plan = planner.plan("صمم نظام إدارة موظفين متكاملًا")
    """

    def __init__(
        self,
        providers: Sequence[Any],
        workspace_root: str | Path,
        tool_registry: Any = None,
        capability_registry: Any = None,
    ) -> None:
        self._providers = list(providers or [])
        self._root = Path(workspace_root).resolve()
        self._tool_registry = tool_registry
        self._capability_registry = capability_registry

    # ── Public API ────────────────────────────────────────────────────────────

    def plan(
        self,
        goal: str,
        context: Optional[Dict[str, Any]] = None,
        workspace_state: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        يولّد خطة تنفيذ منظمة للهدف المعطى.

        يُعيد:
        {
            "status": "ok" | "capability_gap" | "parse_error",
            "plan": { goal_id, goal, success_criteria, tasks, ... } | None,
            "error": str | None,
        }
        """
        if not self._providers:
            return {
                "status": "capability_gap",
                "plan": None,
                "error": "no_inference_provider_available",
                "suggestion": "Configure OPENAI_API_KEY or OLLAMA_ENABLED to enable autonomous planning.",
            }

        goal_id = uuid.uuid4().hex[:8]
        context_block = self._build_context_block(goal_id, context, workspace_state)

        user_prompt = (
            f"الهدف: {goal}\n\n"
            f"goal_id: {goal_id}\n\n"
            f"{context_block}"
        )

        raw = self._call_provider(
            _PLAN_SYSTEM_PROMPT.replace("{goal_id}", goal_id),
            user_prompt,
        )
        if not raw:
            return {
                "status": "capability_gap",
                "plan": None,
                "error": "inference_provider_returned_empty",
            }

        parsed = self._parse_json(raw)
        if parsed is None:
            return {
                "status": "parse_error",
                "plan": None,
                "error": "failed_to_parse_plan_json",
                "raw_response": raw[:500],
            }

        # Ensure goal_id is consistent
        parsed["goal_id"] = parsed.get("goal_id") or goal_id
        parsed["planned_at"] = _now_iso()
        parsed.setdefault("tasks", [])
        parsed.setdefault("success_criteria", [])
        parsed.setdefault("assumptions", [])
        parsed.setdefault("architecture", {})

        return {"status": "ok", "plan": parsed, "error": None}

    def generate_file_content(
        self,
        path: str,
        content_prompt: str,
        goal: str,
        goal_id: str,
        context: Optional[str] = None,
    ) -> Optional[str]:
        """
        يولّد المحتوى الفعلي لملف بناءً على الوصف.

        يُعيد المحتوى كـ string، أو None إذا فشل.
        """
        if not self._providers:
            return None

        lang_hint = self._infer_language(path)
        user_prompt = (
            f"المشروع: {goal}\n"
            f"الملف: {path}\n"
            f"اللغة/النوع: {lang_hint}\n"
            f"المطلوب: {content_prompt}\n"
        )
        if context:
            user_prompt += f"\nسياق إضافي:\n{context}\n"

        return self._call_provider(_CONTENT_SYSTEM_PROMPT, user_prompt)

    def generate_repair_tasks(
        self,
        failed_task: Dict[str, Any],
        error: str,
        goal: str,
        goal_id: str,
    ) -> List[Dict[str, Any]]:
        """
        يولّد مهام إصلاح عند فشل مهمة.
        """
        if not self._providers:
            return []

        user_prompt = (
            f"الهدف: {goal}\n"
            f"المهمة الفاشلة: {json.dumps(failed_task, ensure_ascii=False)}\n"
            f"الخطأ: {error}\n"
        )

        raw = self._call_provider(_REPAIR_SYSTEM_PROMPT, user_prompt)
        if not raw:
            return []

        parsed = self._parse_json(raw)
        if not parsed:
            return []

        repair_tasks = parsed.get("repair_tasks", [])
        # Tag repair tasks so they're identifiable
        for t in repair_tasks:
            t["_repair"] = True
            t["_repairs_task"] = failed_task.get("id", "")
        return repair_tasks

    def evaluate_completion(
        self,
        goal: str,
        success_criteria: List[str],
        execution_results: List[Dict[str, Any]],
        workspace_state: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        يُقيّم اكتمال الهدف بناءً على نتائج التنفيذ.
        """
        if not self._providers:
            # Deterministic fallback: check if all tasks completed
            completed = sum(
                1 for r in execution_results if (r.get("status") == "completed" or r.get("completed", 0) > 0)
            )
            total = len(execution_results)
            complete = total > 0 and completed == total
            return {
                "complete": complete,
                "confidence": 1.0 if complete else 0.0,
                "criteria_met": success_criteria if complete else [],
                "criteria_missing": [] if complete else success_criteria,
                "summary": "اكتملت جميع المهام." if complete else f"اكتملت {completed}/{total} مهام.",
            }

        completed_tasks = [r for r in execution_results if r.get("status") == "completed"]
        failed_tasks = [r for r in execution_results if r.get("status") in {"failed", "blocked"}]

        user_prompt = (
            f"الهدف: {goal}\n"
            f"معايير النجاح:\n" + "\n".join(f"- {c}" for c in success_criteria) + "\n\n"
            f"المهام المكتملة: {len(completed_tasks)}\n"
            f"المهام الفاشلة: {len(failed_tasks)}\n"
            f"تفاصيل النتائج:\n{json.dumps(execution_results[:10], ensure_ascii=False)}\n"
        )

        if workspace_state:
            user_prompt += f"\nحالة مساحة العمل:\n{json.dumps(workspace_state, ensure_ascii=False)[:500]}\n"

        raw = self._call_provider(_EVALUATION_SYSTEM_PROMPT, user_prompt)
        if not raw:
            return {
                "complete": False,
                "confidence": 0.0,
                "criteria_met": [],
                "criteria_missing": success_criteria,
                "summary": "تعذّر تقييم الاكتمال — inference provider غير متاح.",
            }

        parsed = self._parse_json(raw)
        if not parsed:
            return {
                "complete": False,
                "confidence": 0.0,
                "criteria_met": [],
                "criteria_missing": success_criteria,
                "summary": "تعذّر تحليل تقييم الاكتمال.",
            }

        return parsed

    def available_tools(self) -> List[str]:
        """يُعيد قائمة الأدوات المتاحة."""
        base = ["file.create", "file.read", "file.update", "shell.run"]
        if self._tool_registry is not None:
            try:
                registered = [t.get("name") for t in (self._tool_registry.list_tools() or [])]
                registered = [n for n in registered if n]
                if registered:
                    return list(set(base + registered))
            except Exception:
                pass
        return base

    def available_capabilities(self) -> List[str]:
        """يُعيد قائمة القدرات المتاحة."""
        base = ["file_operations", "shell_execution"]
        if self._capability_registry is not None:
            try:
                snap = self._capability_registry.snapshot()
                names = [c.get("name") for c in snap.get("capabilities", [])]
                names = [n for n in names if n]
                if names:
                    return list(set(base + names))
            except Exception:
                pass
        return base

    # ── Private helpers ───────────────────────────────────────────────────────

    def _call_provider(self, system_prompt: str, user_prompt: str) -> Optional[str]:
        """يستدعي أول provider متاح ويُعيد النص."""
        for provider in self._providers:
            try:
                if not provider.is_available():
                    continue
                result = provider.complete(system_prompt, user_prompt)
                if result:
                    return str(result).strip()
            except Exception:
                continue
        return None

    def _parse_json(self, raw: str) -> Optional[Dict[str, Any]]:
        """يحاول تحليل JSON من نص قد يحتوي على markdown."""
        # Remove markdown code fences if present
        text = raw.strip()
        # Try to extract JSON from ```json ... ```
        fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
        if fence_match:
            text = fence_match.group(1).strip()
        # Find the first { ... } block
        brace_match = re.search(r"\{[\s\S]*\}", text)
        if brace_match:
            text = brace_match.group(0)
        try:
            return json.loads(text)
        except (json.JSONDecodeError, ValueError):
            return None

    def _build_context_block(
        self,
        goal_id: str,
        context: Optional[Dict[str, Any]],
        workspace_state: Optional[Dict[str, Any]],
    ) -> str:
        parts: List[str] = []

        if context:
            founder = context.get("founder_context", "")
            if founder:
                parts.append(f"سياق المؤسسة:\n{founder[:300]}")
            active = context.get("active_projects", [])
            if active:
                parts.append("المشاريع النشطة: " + "، ".join(str(p) for p in active[:5]))

        if workspace_state:
            summary = workspace_state.get("summary", "")
            if summary:
                parts.append(f"ملخص مساحة العمل:\n{str(summary)[:300]}")

        runtime_ws = f"09_Assets/runtime_workspace/projects/{goal_id}"
        parts.append(f"مسار المشروع: {runtime_ws}")
        parts.append(f"الأدوات المتاحة: {', '.join(self.available_tools())}")

        return "\n\n".join(parts)

    @staticmethod
    def _infer_language(path: str) -> str:
        """يستنتج لغة البرمجة من امتداد الملف."""
        ext = Path(path).suffix.lower()
        mapping = {
            ".py": "Python",
            ".js": "JavaScript (ES6+)",
            ".ts": "TypeScript",
            ".html": "HTML5",
            ".css": "CSS3",
            ".json": "JSON",
            ".md": "Markdown",
            ".sql": "SQL",
            ".sh": "Bash shell script",
            ".yaml": "YAML",
            ".yml": "YAML",
            ".env": "Environment variables (.env format)",
            ".txt": "Plain text",
            ".jsx": "React JSX",
            ".tsx": "React TSX (TypeScript)",
        }
        return mapping.get(ext, f"ملف {ext}" if ext else "نص عام")
