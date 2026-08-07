"""
scheduler.py
============
P1.4 Scheduler — يحوّل الـ task batch المقبول إلى ترتيب تنفيذي حقيقي.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set


_BLOCKED_STATUSES = {"blocked", "failed"}
_STRING_PRIORITIES = {
    "critical": 400,
    "highest": 350,
    "high": 300,
    "medium": 200,
    "normal": 200,
    "low": 100,
    "lowest": 50,
}


class Scheduler:
    def __init__(self, workspace_root=None, state_manager=None) -> None:
        self._root = workspace_root
        self._state = state_manager

    def schedule(self, tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        task_map: Dict[str, Dict[str, Any]] = {}
        order_index: Dict[str, int] = {}
        blocked_entries: List[Dict[str, Any]] = []
        blocked_ids: Set[str] = set()
        batches: List[Dict[str, Any]] = []
        execution_order: List[str] = []

        for idx, task in enumerate(tasks):
            task_id = str(task.get("id") or f"task-{idx}")
            task_map[task_id] = task
            order_index[task_id] = idx

        cycle = self._detect_cycle(task_map)
        if cycle:
            return {
                "accepted": False,
                "blocked": [{
                    "id": cycle[0],
                    "reason": "dependency_cycle",
                    "detail": " -> ".join(cycle),
                }],
                "batches": [],
                "execution_order": [],
                "summary": {
                    "total": len(tasks),
                    "scheduled": 0,
                    "blocked": len(task_map),
                    "parallel_batches": 0,
                },
            }

        for task_id, task in task_map.items():
            status = str(task.get("status", "")).lower()
            if task.get("blocked") is True or status in _BLOCKED_STATUSES:
                blocked_ids.add(task_id)
                blocked_entries.append({
                    "id": task_id,
                    "reason": "task_blocked",
                    "blocked_by": [],
                })

        changed = True
        while changed:
            changed = False
            for task_id, task in task_map.items():
                if task_id in blocked_ids:
                    continue
                deps = [str(dep) for dep in task.get("depends_on", []) if dep]
                blocked_by = [dep for dep in deps if dep in blocked_ids]
                if blocked_by:
                    blocked_ids.add(task_id)
                    blocked_entries.append({
                        "id": task_id,
                        "reason": "blocked_dependencies",
                        "blocked_by": blocked_by,
                    })
                    changed = True

        remaining: Set[str] = set(task_map.keys()) - blocked_ids
        scheduled: Set[str] = set()

        while remaining:
            ready = [
                task_map[task_id]
                for task_id in remaining
                if all(str(dep) in scheduled for dep in task_map[task_id].get("depends_on", []) if dep)
            ]
            if not ready:
                unresolved = sorted(remaining, key=lambda tid: order_index[tid])
                for task_id in unresolved:
                    blocked_entries.append({
                        "id": task_id,
                        "reason": "unschedulable_dependencies",
                        "blocked_by": [str(dep) for dep in task_map[task_id].get("depends_on", []) if dep],
                    })
                return {
                    "accepted": False,
                    "blocked": blocked_entries,
                    "batches": batches,
                    "execution_order": execution_order,
                    "summary": {
                        "total": len(tasks),
                        "scheduled": len(scheduled),
                        "blocked": len(task_map) - len(scheduled),
                        "parallel_batches": sum(1 for batch in batches if batch["parallel"]),
                    },
                }

            ready.sort(
                key=lambda task: (
                    -self._priority_value(task.get("priority")),
                    order_index[str(task.get("id"))],
                )
            )

            i = 0
            while i < len(ready):
                current = ready[i]
                current_id = str(current.get("id"))
                priority_value = self._priority_value(current.get("priority"))

                if self._is_parallel_safe(current):
                    group = [current]
                    j = i + 1
                    while j < len(ready):
                        candidate = ready[j]
                        if (
                            self._is_parallel_safe(candidate)
                            and self._priority_value(candidate.get("priority")) == priority_value
                        ):
                            group.append(candidate)
                            j += 1
                            continue
                        break
                    task_ids = [str(task.get("id")) for task in group]
                    batches.append({
                        "parallel": len(task_ids) > 1,
                        "task_ids": task_ids,
                        "tasks": group,
                    })
                    for task_id in task_ids:
                        scheduled.add(task_id)
                        remaining.discard(task_id)
                        execution_order.append(task_id)
                    i = j
                    continue

                batches.append({
                    "parallel": False,
                    "task_ids": [current_id],
                    "tasks": [current],
                })
                scheduled.add(current_id)
                remaining.discard(current_id)
                execution_order.append(current_id)
                i += 1

        return {
            "accepted": True,
            "blocked": blocked_entries,
            "batches": batches,
            "execution_order": execution_order,
            "summary": {
                "total": len(tasks),
                "scheduled": len(execution_order),
                "blocked": len(blocked_entries),
                "parallel_batches": sum(1 for batch in batches if batch["parallel"]),
            },
        }

    def _is_parallel_safe(self, task: Dict[str, Any]) -> bool:
        return bool(task.get("parallel_safe", False))

    def _priority_value(self, value: Any) -> int:
        if isinstance(value, (int, float)):
            return int(value)
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in _STRING_PRIORITIES:
                return _STRING_PRIORITIES[normalized]
            try:
                return int(normalized)
            except ValueError:
                return 0
        return 0

    def _detect_cycle(self, task_map: Dict[str, Dict[str, Any]]) -> List[str]:
        visited: Set[str] = set()
        in_stack: Set[str] = set()
        path: List[str] = []

        def dfs(node: str) -> Optional[List[str]]:
            if node in in_stack:
                start = path.index(node)
                return path[start:] + [node]
            if node in visited:
                return None
            visited.add(node)
            in_stack.add(node)
            path.append(node)
            for dep in [str(dep) for dep in task_map.get(node, {}).get("depends_on", []) if dep]:
                if dep in task_map:
                    result = dfs(dep)
                    if result:
                        return result
            path.pop()
            in_stack.discard(node)
            return None

        for node in task_map:
            if node not in visited:
                result = dfs(node)
                if result:
                    return result
        return []
