"""
autonomous_agent.py
===================
AutonomousAgentLoop — حلقة الوكيل الذاتي القائمة على الأهداف.

يحوّل هدفًا عالي المستوى إلى تنفيذ كامل دون intents مسبقة:

    Goal
    → Understand
    → Plan dynamically (DynamicPlanner + inference)
    → Inspect workspace
    → Execute local tasks (via ExecutiveKernel infrastructure)
    → Observe results
    → Detect failures/gaps
    → Re-plan / Repair
    → Retry
    → Verify goal completion
    → Present result to Founder
    → Stop at external effects — request approval

المبادئ:
- LOCAL AUTONOMY: أمير يعمل ذاتيًا داخل runtime_workspace بدون موافقات.
- EXTERNAL EFFECT APPROVAL: موافقة المؤسسة مطلوبة فقط عند نشر خارجي / git push / إلخ.
- FAIL-SAFE: حدود قصوى ضد الحلقات اللانهائية.
"""

from __future__ import annotations

import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ── Safeguard defaults ────────────────────────────────────────────────────────

_DEFAULT_MAX_ITERATIONS = 20
_DEFAULT_MAX_RETRIES_PER_TASK = 3
_DEFAULT_WALL_CLOCK_BUDGET = 300   # seconds
_DEFAULT_MODEL_CALL_BUDGET = 50    # inference provider calls


class AutonomousAgentLoop:
    """
    حلقة الوكيل الذاتي — تنفيذ أي هدف بشكل ذاتي بدون intents مسبقة.

    الاستخدام:
    ----------
    agent = AutonomousAgentLoop(kernel=KERNEL, providers=brain._providers, workspace_root=ROOT)
    report = agent.accept_goal("صمم نظام إدارة موظفين متكاملًا")
    """

    def __init__(
        self,
        kernel: Any,
        providers: Sequence[Any],
        workspace_root: str | Path,
        max_iterations: int = _DEFAULT_MAX_ITERATIONS,
        max_retries_per_task: int = _DEFAULT_MAX_RETRIES_PER_TASK,
        wall_clock_budget: int = _DEFAULT_WALL_CLOCK_BUDGET,
        model_call_budget: int = _DEFAULT_MODEL_CALL_BUDGET,
    ) -> None:
        self._kernel = kernel
        self._workspace_root = Path(workspace_root).resolve()
        self._max_iterations = max_iterations
        self._max_retries_per_task = max_retries_per_task
        self._wall_clock_budget = wall_clock_budget
        self._model_call_budget = model_call_budget

        # Lazy import to avoid circular imports
        from kernel.dynamic_planner import DynamicPlanner
        self._planner = DynamicPlanner(
            providers=providers,
            workspace_root=workspace_root,
            tool_registry=getattr(kernel, "tool_registry", None),
            capability_registry=getattr(kernel, "capabilities", None),
        )

    # ── Public API ────────────────────────────────────────────────────────────

    def accept_goal(
        self,
        goal: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        نقطة الدخول الرئيسية.

        يُعيد تقرير تنفيذ منظم:
        {
            "status": "goal_complete" | "needs_founder_attention" | "external_effect_pending"
                      | "capability_gap" | "failed",
            "goal_id": "...",
            "goal": "...",
            "plan": {...},
            "execution_summary": {...},
            "tasks_completed": [...],
            "tasks_failed": [...],
            "pending_approvals": [...],
            "completion_evaluation": {...},
            "message": "...",
            "started_at": "...",
            "completed_at": "...",
        }
        """
        started_at = _now_iso()
        start_time = time.monotonic()
        model_calls = 0

        report: Dict[str, Any] = {
            "goal": goal,
            "goal_id": "",
            "status": "running",
            "plan": None,
            "execution_summary": {},
            "tasks_completed": [],
            "tasks_failed": [],
            "pending_approvals": [],
            "completion_evaluation": {},
            "message": "",
            "started_at": started_at,
            "completed_at": "",
            "iterations": 0,
            "model_calls": 0,
        }

        try:
            # 1. Inspect workspace
            workspace_state = self._inspect_workspace()

            # 2. Generate plan
            plan_result = self._planner.plan(goal, context=context, workspace_state=workspace_state)
            model_calls += 1

            if plan_result["status"] != "ok":
                report["status"] = "capability_gap"
                report["message"] = (
                    f"تعذّر توليد الخطة: {plan_result.get('error', 'unknown error')}. "
                    f"{plan_result.get('suggestion', '')}"
                )
                report["completed_at"] = _now_iso()
                report["model_calls"] = model_calls
                return report

            plan = plan_result["plan"]
            goal_id = plan["goal_id"]
            report["goal_id"] = goal_id
            report["plan"] = plan

            # Ensure project directory exists in workspace
            project_dir = str(self._workspace_root / "09_Assets" / "runtime_workspace" / "projects" / goal_id)

            # 3. Execute plan tasks
            tasks = list(plan.get("tasks", []))
            completed_tasks: List[Dict[str, Any]] = []
            failed_tasks: List[Dict[str, Any]] = []
            pending_approvals: List[Dict[str, Any]] = []
            iterations = 0
            task_retries: Dict[str, int] = {}

            # Build execution queue with dependency ordering
            task_queue = self._topological_sort(tasks)
            completed_ids: set = set()
            i = 0

            while i < len(task_queue):
                # ── Safeguard checks ──────────────────────────────────────────
                iterations += 1
                if iterations > self._max_iterations:
                    report["status"] = "needs_founder_attention"
                    report["message"] = (
                        f"تجاوز الحد الأقصى للتكرارات ({self._max_iterations}). "
                        "يحتاج إلى مراجعة يدوية."
                    )
                    break

                elapsed = time.monotonic() - start_time
                if elapsed > self._wall_clock_budget:
                    report["status"] = "needs_founder_attention"
                    report["message"] = (
                        f"تجاوز الميزانية الزمنية ({self._wall_clock_budget} ثانية). "
                        "يحتاج إلى مراجعة."
                    )
                    break

                if model_calls > self._model_call_budget:
                    report["status"] = "needs_founder_attention"
                    report["message"] = (
                        f"تجاوز ميزانية استدعاء النموذج ({self._model_call_budget}). "
                        "يحتاج إلى مراجعة."
                    )
                    break

                planner_task = task_queue[i]
                task_id = planner_task.get("id", f"task-{i}")
                i += 1

                # Check if dependencies are satisfied
                deps = planner_task.get("dependencies", [])
                if any(dep not in completed_ids for dep in deps):
                    # Skip for now — dependency not yet complete
                    # (will be re-queued if failed tasks are fixed)
                    failed_tasks.append({
                        "task_id": task_id,
                        "status": "skipped",
                        "reason": "dependency_not_met",
                        "dependencies": deps,
                    })
                    continue

                # Check effect scope — stop at external effects
                if planner_task.get("effect_scope") == "external_effect":
                    approval = {
                        "task_id": task_id,
                        "description": planner_task.get("description", task_id),
                        "tool": planner_task.get("tool", ""),
                        "inputs": planner_task.get("inputs", {}),
                        "requested_at": _now_iso(),
                        "reason": "external_effect_requires_founder_approval",
                    }
                    pending_approvals.append(approval)
                    # Register in kernel approval gate if available
                    self._register_approval(approval)
                    continue

                # Translate to kernel task format
                kernel_task, content_error = self._prepare_kernel_task(
                    planner_task, project_dir, goal, goal_id
                )
                if content_error:
                    model_calls += 1

                if kernel_task is None:
                    failed_tasks.append({
                        "task_id": task_id,
                        "status": "failed",
                        "reason": "task_translation_failed",
                        "error": content_error or "unknown",
                    })
                    continue

                # Execute task
                exec_result = self._execute_kernel_task([kernel_task])
                task_outcome = self._extract_task_outcome(exec_result, task_id)

                if task_outcome["status"] == "completed":
                    completed_tasks.append({
                        "task_id": task_id,
                        "description": planner_task.get("description", ""),
                        "tool": planner_task.get("tool", ""),
                        "status": "completed",
                        "result": task_outcome,
                    })
                    completed_ids.add(task_id)

                else:
                    # Failure — attempt repair
                    retry_count = task_retries.get(task_id, 0)

                    if retry_count < self._max_retries_per_task:
                        # Try to generate repair tasks
                        error_msg = task_outcome.get("reason", str(task_outcome))
                        repair_tasks = self._planner.generate_repair_tasks(
                            failed_task=planner_task,
                            error=error_msg,
                            goal=goal,
                            goal_id=goal_id,
                        )
                        model_calls += 1

                        if repair_tasks:
                            # Insert repair tasks before the current task (re-queued)
                            repaired_planner_task = dict(planner_task)
                            task_retries[task_id] = retry_count + 1
                            # Queue repair tasks + retry current
                            task_queue = task_queue[:i] + repair_tasks + [repaired_planner_task] + task_queue[i:]
                        else:
                            # No repair possible — mark as failed
                            failed_tasks.append({
                                "task_id": task_id,
                                "description": planner_task.get("description", ""),
                                "status": "failed",
                                "reason": error_msg,
                                "retries": retry_count,
                            })
                    else:
                        # Max retries exceeded
                        failed_tasks.append({
                            "task_id": task_id,
                            "description": planner_task.get("description", ""),
                            "status": "failed_permanently",
                            "reason": task_outcome.get("reason", "max_retries_exceeded"),
                            "retries": retry_count,
                        })

            report["iterations"] = iterations
            report["model_calls"] = model_calls
            report["tasks_completed"] = completed_tasks
            report["tasks_failed"] = failed_tasks
            report["pending_approvals"] = pending_approvals

            # 4. Evaluate goal completion
            if report["status"] == "running":
                completion = self._planner.evaluate_completion(
                    goal=goal,
                    success_criteria=plan.get("success_criteria", []),
                    execution_results=self._flatten_results(completed_tasks, failed_tasks),
                    workspace_state=self._inspect_workspace(),
                )
                model_calls += 1
                report["completion_evaluation"] = completion
                report["model_calls"] = model_calls

                if pending_approvals:
                    report["status"] = "external_effect_pending"
                    report["message"] = (
                        f"اكتمل العمل المحلي. {len(pending_approvals)} مهمة تحتاج موافقة للتأثيرات الخارجية."
                    )
                elif completion.get("complete"):
                    report["status"] = "goal_complete"
                    report["message"] = completion.get("summary", "اكتمل الهدف بنجاح.")
                elif failed_tasks:
                    report["status"] = "needs_founder_attention"
                    report["message"] = (
                        f"اكتملت {len(completed_tasks)} مهمة، فشلت {len(failed_tasks)} مهمة. "
                        + completion.get("summary", "")
                    )
                else:
                    report["status"] = "goal_complete"
                    report["message"] = completion.get("summary", "اكتملت جميع المهام.")

            report["execution_summary"] = {
                "total_tasks": len(tasks),
                "completed": len(completed_tasks),
                "failed": len(failed_tasks),
                "pending_approval": len(pending_approvals),
                "elapsed_seconds": round(time.monotonic() - start_time, 1),
            }

        except Exception as exc:
            report["status"] = "failed"
            report["message"] = f"خطأ غير متوقع في حلقة الوكيل: {str(exc)}"

        report["completed_at"] = _now_iso()
        return report

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _inspect_workspace(self) -> Dict[str, Any]:
        """يفحص حالة مساحة العمل الحالية."""
        try:
            workspace = getattr(self._kernel, "workspace", None)
            if workspace is not None:
                scan = workspace.scan()
                return {
                    "summary": str(workspace.build_executive_summary(scan))[:500],
                    "scan": scan,
                }
        except Exception:
            pass
        return {"summary": "", "scan": {}}

    def _prepare_kernel_task(
        self,
        planner_task: Dict[str, Any],
        project_dir: str,
        goal: str,
        goal_id: str,
    ) -> "tuple[Optional[Dict[str, Any]], Optional[str]]":
        """
        يُترجم مهمة المخطط إلى صيغة kernel task.

        يُعيد (kernel_task, error_message).
        """
        tool = planner_task.get("tool", "")
        inputs = planner_task.get("inputs", {}) or {}
        task_id = planner_task.get("id", str(uuid.uuid4().hex[:8]))
        content_error: Optional[str] = None

        if tool in ("file.create", "file.update"):
            path = inputs.get("path", "")
            if not path:
                return None, "missing_path_in_inputs"

            # Normalize path — ensure it's inside the project workspace
            abs_path = self._resolve_safe_path(path, project_dir)
            if abs_path is None:
                return None, f"path_outside_sandbox: {path}"

            # Generate actual file content
            content_prompt = inputs.get("content_prompt", "")
            content = inputs.get("content", "")

            if not content and content_prompt:
                generated = self._planner.generate_file_content(
                    path=abs_path,
                    content_prompt=content_prompt,
                    goal=goal,
                    goal_id=goal_id,
                )
                if generated:
                    content = generated
                else:
                    content_error = "content_generation_failed"
                    # Use empty content placeholder if generation failed
                    content = f"# TODO: {content_prompt}\n"

            action = "write"  # both create and update map to "write"
            return (
                {
                    "id": task_id,
                    "action": action,
                    "executor": "file",
                    "target": abs_path,
                    "content": content,
                    "priority": planner_task.get("priority", "normal"),
                    "description": planner_task.get("description", ""),
                },
                content_error,
            )

        elif tool == "file.read":
            path = inputs.get("path", "")
            if not path:
                return None, "missing_path_in_inputs"

            abs_path = self._resolve_safe_path(path, project_dir)
            if abs_path is None:
                return None, f"path_outside_sandbox: {path}"

            return (
                {
                    "id": task_id,
                    "action": "read",
                    "executor": "file",
                    "target": abs_path,
                    "priority": planner_task.get("priority", "normal"),
                    "description": planner_task.get("description", ""),
                },
                None,
            )

        elif tool == "shell.run":
            command = inputs.get("command", "")
            if not command:
                return None, "missing_command_in_inputs"

            # Validate command is not an external effect
            if self._is_dangerous_command(command):
                return None, f"command_classified_as_external_effect: {command}"

            cwd = inputs.get("cwd") or project_dir
            # shell tasks need a `target` inside sandbox for PlanValidator
            target = self._resolve_safe_path(cwd, project_dir) or project_dir

            return (
                {
                    "id": task_id,
                    "action": "run",
                    "executor": "shell",
                    "command": command if isinstance(command, list) else command,
                    "target": target,
                    "cwd": cwd,
                    "priority": planner_task.get("priority", "normal"),
                    "description": planner_task.get("description", ""),
                },
                None,
            )

        else:
            return None, f"unsupported_tool: {tool}"

    def _resolve_safe_path(
        self, path: str, project_dir: str
    ) -> Optional[str]:
        """
        يُحوّل مسارًا إلى مسار مطلق ويتحقق أنه داخل runtime_workspace.

        يُعيد المسار المطلق أو None إذا كان خارج الحدود.
        """
        try:
            # If already absolute
            p = Path(path)
            if not p.is_absolute():
                # Try relative to workspace root first
                abs_p = (self._workspace_root / path).resolve()
            else:
                abs_p = p.resolve()

            # Must be inside runtime_workspace
            runtime_ws = (self._workspace_root / "09_Assets" / "runtime_workspace").resolve()
            try:
                abs_p.relative_to(runtime_ws)
                return str(abs_p)
            except ValueError:
                pass

            # Fallback: place under project dir
            rel_name = Path(path).name
            fallback = (Path(project_dir) / rel_name).resolve()
            try:
                fallback.relative_to(runtime_ws)
                return str(fallback)
            except ValueError:
                return None
        except Exception:
            return None

    @staticmethod
    def _is_dangerous_command(command: Any) -> bool:
        """يكتشف الأوامر ذات التأثير الخارجي."""
        if isinstance(command, list):
            cmd_str = " ".join(str(c) for c in command)
        else:
            cmd_str = str(command)
        danger_patterns = [
            "git push", "git merge", "git checkout main",
            "npm publish", "pip publish", "twine upload",
            "railway up", "railway deploy",
            "heroku", "vercel deploy", "netlify deploy",
            "docker push", "kubectl apply",
            "rm -rf /", "sudo rm",
        ]
        cmd_lower = cmd_str.lower()
        return any(p in cmd_lower for p in danger_patterns)

    def _execute_kernel_task(self, kernel_tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """يُنفّذ مهام عبر ExecutiveKernel.execute_task()."""
        try:
            return self._kernel.execute_task(
                kernel_tasks,
                guardian={"status": "pass"},
                request_type="execution",
                intent="autonomous_goal",
                requested_by="autonomous_agent_loop",
            )
        except Exception as exc:
            return {
                "accepted": False,
                "execution": {
                    "completed": 0,
                    "failed": 1,
                    "blocked": 0,
                    "results": [
                        {
                            "task_id": kernel_tasks[0].get("id") if kernel_tasks else "unknown",
                            "status": "failed",
                            "reason": str(exc),
                        }
                    ],
                },
            }

    @staticmethod
    def _extract_task_outcome(
        exec_result: Dict[str, Any],
        task_id: str,
    ) -> Dict[str, Any]:
        """يستخلص نتيجة مهمة من مخرج execute_task."""
        execution = exec_result.get("execution", {})
        results = execution.get("results", [])

        for r in results:
            if r.get("task_id") == task_id or r.get("id") == task_id:
                return r

        # Fallback: if exactly one result, use it
        if len(results) == 1:
            return results[0]

        # Infer from aggregate
        if execution.get("completed", 0) > 0:
            return {"task_id": task_id, "status": "completed"}
        if execution.get("failed", 0) > 0:
            return {
                "task_id": task_id,
                "status": "failed",
                "reason": "execution_failed",
            }
        if execution.get("blocked", 0) > 0:
            return {
                "task_id": task_id,
                "status": "blocked",
                "reason": "execution_blocked",
            }
        if not exec_result.get("accepted"):
            validation = exec_result.get("validation", {})
            blocked_reasons = validation.get("blocked", [])
            return {
                "task_id": task_id,
                "status": "failed",
                "reason": "; ".join(blocked_reasons) if blocked_reasons else "plan_validation_failed",
            }

        return {"task_id": task_id, "status": "completed"}

    def _register_approval(self, approval: Dict[str, Any]) -> None:
        """يُسجّل طلب موافقة في ApprovalGate."""
        try:
            approvals = getattr(self._kernel, "approvals", None)
            if approvals is not None:
                approvals.request(
                    action="external_effect",
                    description=approval.get("description", "external_effect"),
                    requested_by="autonomous_agent_loop",
                    context=approval,
                )
        except Exception:
            pass

    @staticmethod
    def _topological_sort(tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        يُرتّب المهام حسب التبعيات (Kahn's algorithm).
        يحتفظ بالترتيب الأصلي للمهام غير المترابطة.
        """
        if not tasks:
            return []

        task_map = {t.get("id", f"_t{idx}"): t for idx, t in enumerate(tasks)}
        in_degree: Dict[str, int] = {tid: 0 for tid in task_map}
        dependents: Dict[str, List[str]] = {tid: [] for tid in task_map}

        for tid, task in task_map.items():
            for dep in (task.get("dependencies") or []):
                if dep in in_degree:
                    in_degree[tid] = in_degree.get(tid, 0) + 1
                    dependents[dep].append(tid)

        # Start with tasks that have no dependencies (preserve original order)
        queue = [t for t in tasks if in_degree.get(t.get("id", ""), 0) == 0]
        result: List[Dict[str, Any]] = []

        while queue:
            task = queue.pop(0)
            result.append(task)
            tid = task.get("id", "")
            for dep_tid in dependents.get(tid, []):
                in_degree[dep_tid] -= 1
                if in_degree[dep_tid] == 0:
                    next_task = task_map.get(dep_tid)
                    if next_task is not None:
                        queue.append(next_task)

        # Append any tasks that weren't processed (cycle or missing deps — append as-is)
        processed_ids = {t.get("id", "") for t in result}
        for t in tasks:
            if t.get("id", "") not in processed_ids:
                result.append(t)

        return result

    @staticmethod
    def _flatten_results(
        completed: List[Dict[str, Any]],
        failed: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """يدمج نتائج المهام المكتملة والفاشلة."""
        flat = []
        for t in completed:
            flat.append({"task_id": t.get("task_id"), "status": "completed"})
        for t in failed:
            flat.append({"task_id": t.get("task_id"), "status": t.get("status", "failed")})
        return flat


# ── Router helper (used by ameer_server.py) ───────────────────────────────────

_AUTONOMOUS_GOAL_PATTERNS = [
    # Arabic multi-step goal indicators
    "نظام متكامل",
    "نظام كامل",
    "صمم وابنِ",
    "صمم وابن",
    "اصنع نظام",
    "ابنِ نظام",
    "ابن نظام",
    "أنشئ نظام",
    "انشئ نظام",
    "واجهة احترافية",
    "لوحة إدارة",
    "لوحة تحكم",
    "قاعدة بيانات",
    "اختبره وأصلح",
    "جهزه للنشر",
    "backend",
    "frontend",
    "api server",
    "rest api",
    "full stack",
    "fullstack",
    # English multi-step goal indicators
    "design and build",
    "build a complete",
    "build a full",
    "create a complete",
    "create a full",
    "build and test",
    "integrated system",
    "management system",
    "with database",
    "admin panel",
    "admin dashboard",
    "employee management",
    "inventory management",
    "prepare for deployment",
    "ready for production",
]

# Patterns that indicate a simple command (not autonomous)
_SIMPLE_COMMAND_PATTERNS = [
    "الصفحة الرئيسية",
    "صفحة رئيسية",
    "homepage",
    "home page",
    "index.html",
    "اقرأ",
    "read",
    "show",
    "اعرض",
    "شغّل الاختبارات",
    "run test",
    "run tests",
    "مرحبا",
    "أهلا",
    "hello",
    "hi",
]


def is_autonomous_goal(query: str) -> bool:
    """
    يكتشف هل الطلب هدف ذاتي متعدد الخطوات أم أمر بسيط.

    يُعيد True للأهداف المعقدة التي تستفيد من AutonomousAgentLoop.
    """
    if not query or len(query) < 20:
        return False

    q_lower = query.lower()

    # Exclude simple known commands first
    for pattern in _SIMPLE_COMMAND_PATTERNS:
        if pattern.lower() in q_lower:
            return False

    # Check for autonomous goal patterns
    matches = sum(1 for p in _AUTONOMOUS_GOAL_PATTERNS if p.lower() in q_lower)

    # Require at least one explicit pattern match
    # OR a long goal (> 100 chars) that contains execution verbs
    if matches >= 1:
        return True

    execution_verbs = ["ابن", "أنشئ", "صمم", "build", "create", "design", "develop", "implement"]
    has_exec_verb = any(v.lower() in q_lower for v in execution_verbs)
    return has_exec_verb and len(query) > 100
