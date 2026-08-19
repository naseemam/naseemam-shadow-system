from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from kernel.execution_authorization import ExecutionAuthorization
from kernel.executor_file import FileExecutor
from kernel.plan_validator import PlanValidator
from kernel.task_decomposer import TaskDecomposer


# Founder policy: Ameer owns the entire repository and its working
# environment.  It may read, create, and update any repository path, including
# configuration, CI, durable state, and environment files.  The only filesystem
# boundary is structural: a tool may never escape the repository root.  Delete
# and publish remain separately gated by the founder-approval flow.
REPOSITORY_WRITE_PREFIXES: tuple[str, ...] = ()
REPOSITORY_WRITE_FILES: set[str] = set()
REPOSITORY_READ_PREFIXES = REPOSITORY_WRITE_PREFIXES
REPOSITORY_READ_FILES = REPOSITORY_WRITE_FILES
DENIED_PREFIXES: tuple[str, ...] = ()
DENIED_NAMES: set[str] = set()
_REPOSITORY_SCOPE_KIND = "controlled_repository"
_FILE_CREATE_TOOL_NAME = "file.create"
_FILE_CREATE_ACTION = "write"
_FILE_READ_TOOL_NAME = "file.read"
_FILE_READ_ACTION = "read"


def _repository_permission_scope(*, tool_name: str, action: str) -> str:
    return json.dumps(
        {
            "tool_name": tool_name,
            "action": action,
            "scope_kind": _REPOSITORY_SCOPE_KIND,
            "allowed_prefixes": list(REPOSITORY_WRITE_PREFIXES),
            "allowed_files": sorted(REPOSITORY_WRITE_FILES),
            "denied_prefixes": list(DENIED_PREFIXES),
            "denied_names": sorted(DENIED_NAMES),
        },
        ensure_ascii=False,
        sort_keys=True,
    )


def repository_file_create_permission_scope() -> str:
    return _repository_permission_scope(tool_name=_FILE_CREATE_TOOL_NAME, action=_FILE_CREATE_ACTION)


def repository_file_read_permission_scope() -> str:
    return _repository_permission_scope(tool_name=_FILE_READ_TOOL_NAME, action=_FILE_READ_ACTION)


class ControlledRepositoryPolicy:
    def __init__(self, workspace_root: str | Path) -> None:
        self.root = Path(workspace_root).resolve()

    @staticmethod
    def _normalize(target: str) -> str:
        normalized = str(target or "").strip().replace("\\", "/")
        while normalized.startswith("./"):
            normalized = normalized[2:]
        return normalized

    def is_allowed(self, target: str) -> bool:
        normalized = self._normalize(target)
        if not normalized:
            return False
        raw = Path(normalized)
        if raw.is_absolute() or ".." in raw.parts:
            return False
        if raw.name in DENIED_NAMES:
            return False
        if any(normalized == p or normalized.startswith(p + "/") for p in DENIED_PREFIXES):
            return False
        # The request is structurally inside the repository and the Founder has
        # delegated full read/write authority to Ameer.  Destructive effects are
        # enforced later by the approval gate, not by this path policy.
        return True

    def resolve(self, target: str) -> Path:
        if not self.is_allowed(target):
            raise ValueError("target_outside_controlled_repository")
        resolved = (self.root / self._normalize(target)).resolve()
        if not resolved.is_relative_to(self.root):
            raise ValueError("target_outside_repository")
        return resolved


class RepositoryFileExecutor(FileExecutor):
    def __init__(self, workspace_root: str | Path) -> None:
        super().__init__(workspace_root)
        self._repo_policy = ControlledRepositoryPolicy(workspace_root)

    def _resolve_target(self, target: str) -> Path:
        return self._repo_policy.resolve(target)


class RepositoryPlanValidator(PlanValidator):
    def __init__(self, workspace_root: str | Path, **kwargs: Any) -> None:
        super().__init__(workspace_root, **kwargs)
        self._repo_policy = ControlledRepositoryPolicy(workspace_root)

    def _check_sandbox(self, target: str) -> bool:
        if "://" in str(target):
            return False
        return not self._repo_policy.is_allowed(str(target))


class RepositoryExecutionAuthorization(ExecutionAuthorization):
    # Lets ToolDispatcher defer path-level enforcement to this authorization
    # layer when the live controlled-repository kernel is active.  The policy
    # below still permits only the explicit repository surface and rejects
    # secrets, CI, backups, traversal, and every unlisted path.
    controlled_repository_scope = True

    def _file_read_scope_denial_reason(
        self,
        *,
        action: str,
        context: Dict[str, Any] | None,
        perm_card: Dict[str, Any],
    ) -> str:
        policy = self._parse_scope_policy(perm_card.get("scope"))
        required = self._parse_scope_policy(repository_file_read_permission_scope())
        if policy != required:
            return "Permission scope does not authorize controlled repository file.read"
        if action != _FILE_READ_ACTION:
            return "Permission scope is limited to file.read/read only"

        safe_context = context or {}
        tool_name = str(safe_context.get("tool_name") or "").strip().lower()
        if tool_name != _FILE_READ_TOOL_NAME:
            return "Permission scope requires registry-owned tool file.read"

        target = safe_context.get("target")
        if not isinstance(target, str) or not target.strip():
            return "Permission scope requires a controlled repository target"

        repo_policy = ControlledRepositoryPolicy(self._root)
        if not repo_policy.is_allowed(target):
            return "Permission scope denies target outside controlled repository paths"
        return ""

    def _file_create_scope_denial_reason(
        self,
        *,
        action: str,
        context: Dict[str, Any] | None,
        perm_card: Dict[str, Any],
    ) -> str:
        policy = self._parse_scope_policy(perm_card.get("scope"))
        required = self._parse_scope_policy(repository_file_create_permission_scope())
        if policy != required:
            return "Permission scope does not authorize controlled repository file.create"
        if action != _FILE_CREATE_ACTION:
            return "Permission scope is limited to file.create/write only"

        safe_context = context or {}
        tool_name = str(safe_context.get("tool_name") or "").strip().lower()
        if tool_name != _FILE_CREATE_TOOL_NAME:
            return "Permission scope requires registry-owned tool file.create"

        target = safe_context.get("target")
        if not isinstance(target, str) or not target.strip():
            return "Permission scope requires a controlled repository target"

        repo_policy = ControlledRepositoryPolicy(self._root)
        if not repo_policy.is_allowed(target):
            return "Permission scope denies target outside controlled repository paths"
        return ""


class RepositoryTaskDecomposer:
    LIVE_MARKERS = (
        "الموقع الحقيقي",
        "الواجهة الحقيقية",
        "المستودع",
        "الكود الحقيقي",
        "live site",
        "live website",
        "repository",
        "repo",
        "production ui",
    )

    def __init__(self, workspace_root: str) -> None:
        self._base = TaskDecomposer(workspace_root)

    def decompose(self, command: str) -> Dict[str, Any]:
        result = self._base.decompose(command)
        lower = (command or "").lower()
        if not any(marker.lower() in lower for marker in self.LIVE_MARKERS):
            return result

        intent = str(result.get("intent") or "")
        tasks = list(result.get("tasks") or [])
        if intent == "build_homepage":
            mapping = {
                "/home/index.html": "/web/index.html",
                "/home/style.css": "/web/style.css",
                "/home/script.js": "/web/script.js",
            }
            for task in tasks:
                target = str(task.get("target") or "")
                for old_suffix, new_suffix in mapping.items():
                    if target.endswith(old_suffix):
                        task["target"] = "09_Assets" + new_suffix
                        task["repository_scope"] = "controlled"
                        break
        elif intent == "build_generic":
            for task in tasks:
                target = str(task.get("target") or "")
                marker = "09_Assets/runtime_workspace/projects/"
                if target.startswith(marker):
                    task["target"] = "09_Assets/web/generated/" + target[len(marker):]
                    task["repository_scope"] = "controlled"

        result["tasks"] = tasks
        result["repository_execution"] = True
        return result
