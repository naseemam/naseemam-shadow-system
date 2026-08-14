from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from kernel.execution_authorization import ExecutionAuthorization
from kernel.executor_file import FileExecutor
from kernel.plan_validator import PlanValidator
from kernel.task_decomposer import TaskDecomposer


REPOSITORY_WRITE_PREFIXES = (
    "06_Code",
    "07_Tests",
    "09_Assets/web",
    "09_Assets/runtime_workspace",
)
REPOSITORY_WRITE_FILES = {
    "ameer_server.py",
    "ameer_runtime.py",
    "start_ameer.py",
    "railway.toml",
    "requirements.txt",
}
DENIED_PREFIXES = (
    ".git",
    ".github",
    ".ameer",
    "08_Backups",
    "__pycache__",
)
DENIED_NAMES = {
    ".env",
    ".env.local",
    ".env.production",
    ".env.development",
}
_REPOSITORY_SCOPE_KIND = "controlled_repository"
_FILE_CREATE_TOOL_NAME = "file.create"
_FILE_CREATE_ACTION = "write"


def repository_file_create_permission_scope() -> str:
    return json.dumps(
        {
            "tool_name": _FILE_CREATE_TOOL_NAME,
            "action": _FILE_CREATE_ACTION,
            "scope_kind": _REPOSITORY_SCOPE_KIND,
            "allowed_prefixes": list(REPOSITORY_WRITE_PREFIXES),
            "allowed_files": sorted(REPOSITORY_WRITE_FILES),
            "denied_prefixes": list(DENIED_PREFIXES),
            "denied_names": sorted(DENIED_NAMES),
        },
        ensure_ascii=False,
        sort_keys=True,
    )


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
        if raw.name in DENIED_NAMES or raw.name.startswith(".env"):
            return False
        if any(normalized == p or normalized.startswith(p + "/") for p in DENIED_PREFIXES):
            return False
        if normalized in REPOSITORY_WRITE_FILES:
            return True
        return any(
            normalized == prefix or normalized.startswith(prefix + "/")
            for prefix in REPOSITORY_WRITE_PREFIXES
        )

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
