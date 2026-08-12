from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Optional


_REGISTRY_OWNED_FIELDS = frozenset(
    {"capability", "capability_name", "action", "risk_level", "approval_required"}
)
_FILE_READ_SCOPE_OVERRIDE_FIELDS = frozenset(
    {
        "scope",
        "scope_kind",
        "scope_root",
        "workspace_root",
        "runtime_workspace",
        "trusted_scope",
        "allowed_root",
        "caller_scope_override",
    }
)

# Mapping from tool-name prefix to executor key used in _executors dict.
_TOOL_PREFIX_TO_EXECUTOR: dict[str, str] = {
    "file.": "file",
    "shell.": "shell",
}


class ToolDispatcher:
    """Fail-closed tool dispatch contract: resolve metadata, evaluate boundary, return result."""

    def __init__(
        self,
        *,
        tool_registry=None,
        execution_boundary=None,
        execution_authorization=None,
        approval_gate=None,
        executor=None,
        shell_executor=None,
        workspace_root: str | Path | None = None,
    ) -> None:
        self._tool_registry = tool_registry
        self._execution_boundary = execution_boundary
        self._execution_authorization = execution_authorization
        self._approval_gate = approval_gate
        # Backward-compatible single executor (used for file.*); also stored in the map.
        self._executor = executor
        self._workspace_root = Path(workspace_root).resolve() if workspace_root is not None else None

        # Named executor map — allows per-tool-prefix routing without bypassing authorization.
        self._executors: dict[str, Any] = {}
        if executor is not None:
            self._executors["file"] = executor
        if shell_executor is not None:
            self._executors["shell"] = shell_executor

    def dispatch(
        self,
        *,
        tool_name: str,
        context: Optional[Mapping[str, Any]] = None,
        guardian: Optional[Mapping[str, Any]] = None,
        request_type: str = "execution",
        intent: str = "build_homepage",
        requested_by: str = "executive_kernel",
    ) -> dict[str, Any]:
        if not tool_name or not isinstance(tool_name, str):
            return self._deny("tool_not_registered")

        if self._tool_registry is None:
            return self._deny("tool_registry_unavailable")

        resolve_fn = getattr(self._tool_registry, "resolve", None)
        get_fn = getattr(self._tool_registry, "get", None)
        if not callable(resolve_fn) and not callable(get_fn):
            return self._deny("tool_registry_unavailable")

        caller_context = dict(context or {})
        sanitized_context = {
            key: value
            for key, value in caller_context.items()
            if key not in _REGISTRY_OWNED_FIELDS
        }

        try:
            if callable(resolve_fn):
                tool_def = resolve_fn(tool_name, sanitized_context)
            else:
                tool_def = get_fn(tool_name)
        except KeyError:
            return self._deny("tool_not_registered")
        except ValueError as exc:
            return self._deny("tool_policy_denied", detail={"error": str(exc)})
        except Exception:
            return self._deny("tool_registry_unavailable")

        capability_name = getattr(tool_def, "capability", "")
        action = getattr(tool_def, "action", "")
        risk_level = getattr(tool_def, "risk_level", "")
        if not capability_name or not action or not risk_level:
            return self._deny("tool_metadata_missing")

        execution_request = {
            "tool_name": tool_name,
            "capability_name": capability_name,
            "action": action,
            "risk_level": risk_level,
            "context": sanitized_context,
        }

        if self._execution_boundary is None:
            return self._deny("execution_boundary_unavailable", execution_request)

        evaluate_fn = getattr(self._execution_boundary, "evaluate", None)
        if not callable(evaluate_fn):
            return self._deny("execution_boundary_unavailable", execution_request)

        if not guardian:
            return self._deny("guardian_missing", execution_request)

        if self._execution_authorization is None:
            return self._deny("execution_authorization_missing", execution_request)

        auth_check = getattr(self._execution_authorization, "check", None)
        if not callable(auth_check):
            return self._deny("execution_authorization_unavailable", execution_request)

        if self._approval_gate is None and action in {"delete", "publish", "external", "financial"}:
            return self._deny("approval_gate_required_missing", execution_request)

        policy_result = self._enforce_tool_policy(tool_name, tool_def, sanitized_context, execution_request)
        if isinstance(policy_result, dict) and policy_result.get("decision") == "DENY":
            return policy_result
        validated_context = policy_result or sanitized_context

        try:
            boundary_result = evaluate_fn(
                guardian=dict(guardian),
                request_type=request_type,
                intent=intent,
                capability_name=capability_name,
                action=action,
                context={
                    **validated_context,
                    "tool_name": tool_name,
                    "risk_level": risk_level,
                },
                requested_by=requested_by,
            )
        except Exception as exc:
            return self._deny(
                "execution_boundary_unavailable",
                execution_request,
                detail={"error": str(exc)},
            )

        decision = self._decision_from_boundary(boundary_result)
        result = {
            "decision": decision,
            "allowed": decision == "ALLOW",
            "reason": getattr(boundary_result, "reason", "boundary_result_missing"),
            "execution_request": execution_request,
            "boundary_result": boundary_result,
            "executed": False,
            "result": None,
        }
        if decision != "ALLOW":
            return result

        execute_fn = self._resolve_executor(tool_name)
        if not callable(execute_fn):
            return self._deny("executor_unavailable", execution_request)
        payload = validated_context.get("executor_payload", validated_context)
        try:
            execution_result = execute_fn(payload)
        except Exception as exc:
            return {
                **result,
                "decision": "DENY",
                "allowed": False,
                "reason": "executor_unavailable",
                "detail": {"error": str(exc)},
            }
        result["executed"] = True
        result["result"] = execution_result
        return result

    @staticmethod
    def _decision_from_boundary(boundary_result: Any) -> str:
        verdict = getattr(boundary_result, "verdict", None)
        if hasattr(verdict, "value"):
            value = str(verdict.value).strip().lower()
        else:
            value = str(verdict).strip().lower()

        if value == "allow":
            return "ALLOW"
        if value == "pending":
            return "PENDING"
        return "DENY"

    def _resolve_executor(self, tool_name: str) -> Any:
        """Return the executor callable for *tool_name*, checking prefix map first."""
        for prefix, key in _TOOL_PREFIX_TO_EXECUTOR.items():
            if tool_name.startswith(prefix):
                executor = self._executors.get(key)
                if callable(executor):
                    return executor
        # Fallback to legacy single-executor for backward compatibility.
        return self._executor

    def _enforce_tool_policy(
        self,
        tool_name: str,
        tool_def: Any,
        context: Mapping[str, Any],
        execution_request: dict[str, Any],
    ) -> Optional[Mapping[str, Any] | dict[str, Any]]:
        if tool_name == "file.read":
            return self._enforce_file_read_policy(tool_def, context, execution_request)
        if tool_name == "file.create":
            return self._enforce_file_create_policy(tool_def, context, execution_request)
        if tool_name == "shell.run":
            return self._enforce_shell_run_policy(tool_def, context, execution_request)
        return None

    def _enforce_shell_run_policy(
        self,
        tool_def: Any,
        context: Mapping[str, Any],
        execution_request: dict[str, Any],
    ) -> Mapping[str, Any] | dict[str, Any]:
        """Validate shell.run context; ensure command is present and workspace-bound."""
        command = context.get("command")
        if not command or (isinstance(command, str) and not command.strip()):
            return self._deny(
                "shell_run_policy_denied",
                execution_request,
                detail={"error": "missing_command"},
            )

        workspace_root = self._resolve_workspace_root()
        raw_cwd = context.get("cwd")
        if raw_cwd and workspace_root:
            candidate = Path(str(raw_cwd).strip())
            resolved = (
                candidate.resolve()
                if candidate.is_absolute()
                else (workspace_root / candidate).resolve()
            )
            if not resolved.is_relative_to(workspace_root):
                return self._deny(
                    "shell_run_cwd_outside_workspace",
                    execution_request,
                    detail={"cwd": raw_cwd},
                )

        trusted_context = dict(context)
        trusted_payload: dict = dict(context.get("executor_payload") or {})
        trusted_payload["command"] = command
        trusted_payload["action"] = str(getattr(tool_def, "action", "run"))
        trusted_context["executor_payload"] = trusted_payload
        execution_request["context"] = trusted_context
        return trusted_context

    def _enforce_file_create_policy(
        self,
        tool_def: Any,
        context: Mapping[str, Any],
        execution_request: dict[str, Any],
    ) -> Mapping[str, Any] | dict[str, Any]:
        if self._contains_scope_override(context):
            return self._deny(
                "file_create_scope_override_denied",
                execution_request,
                detail={"fields": sorted(_FILE_READ_SCOPE_OVERRIDE_FIELDS.intersection(context))},
            )

        target = context.get("target")
        if not isinstance(target, str) or not target.strip():
            return self._deny(
                "file_create_scope_denied",
                execution_request,
                detail={"error": "missing_target"},
            )

        workspace_root = self._resolve_workspace_root()
        scope_root = self._resolve_scope_root(tool_def, workspace_root)
        if workspace_root is None or scope_root is None:
            return self._deny(
                "file_create_scope_denied",
                execution_request,
                detail={"error": "scope_root_unavailable"},
            )

        try:
            raw_target = Path(target.strip())
            resolved = (
                raw_target.resolve()
                if raw_target.is_absolute()
                else (workspace_root / raw_target).resolve()
            )
            if not resolved.is_relative_to(scope_root):
                raise ValueError("target_outside_file_create_scope")
            normalized_target = str(resolved.relative_to(workspace_root)).replace("\\", "/")
        except ValueError as exc:
            return self._deny(
                "file_create_scope_denied",
                execution_request,
                detail={"error": str(exc), "target": target},
            )

        payload = context.get("executor_payload")
        if payload is not None and not isinstance(payload, Mapping):
            return self._deny(
                "file_create_scope_denied",
                execution_request,
                detail={"error": "invalid_executor_payload"},
            )
        if isinstance(payload, Mapping):
            if self._contains_scope_override(payload):
                return self._deny(
                    "file_create_scope_override_denied",
                    execution_request,
                    detail={"fields": sorted(_FILE_READ_SCOPE_OVERRIDE_FIELDS.intersection(payload))},
                )
            payload_target = payload.get("target")
            if payload_target is not None and str(payload_target).strip() != target.strip():
                return self._deny(
                    "file_create_scope_override_denied",
                    execution_request,
                    detail={"error": "executor_payload_target_override"},
                )

        trusted_payload = dict(payload or {})
        trusted_payload["target"] = str(resolved.relative_to(workspace_root)).replace("\\", "/")
        trusted_payload["action"] = str(tool_def.action)

        trusted_context = dict(context)
        trusted_context["target"] = normalized_target
        trusted_context["executor_payload"] = trusted_payload
        execution_request["context"] = trusted_context
        return trusted_context

    def _enforce_file_read_policy(
        self,
        tool_def: Any,
        context: Mapping[str, Any],
        execution_request: dict[str, Any],
    ) -> Mapping[str, Any] | dict[str, Any]:
        if self._contains_scope_override(context):
            return self._deny(
                "file_read_scope_override_denied",
                execution_request,
                detail={"fields": sorted(_FILE_READ_SCOPE_OVERRIDE_FIELDS.intersection(context))},
            )

        target = context.get("target")
        if not isinstance(target, str) or not target.strip():
            return self._deny(
                "file_read_scope_denied",
                execution_request,
                detail={"error": "missing_target"},
            )

        workspace_root = self._resolve_workspace_root()
        scope_root = self._resolve_scope_root(tool_def, workspace_root)
        if workspace_root is None or scope_root is None:
            return self._deny(
                "file_read_scope_denied",
                execution_request,
                detail={"error": "scope_root_unavailable"},
            )

        payload = context.get("executor_payload")
        if payload is not None and not isinstance(payload, Mapping):
            return self._deny(
                "file_read_scope_denied",
                execution_request,
                detail={"error": "invalid_executor_payload"},
            )
        if isinstance(payload, Mapping):
            if self._contains_scope_override(payload):
                return self._deny(
                    "file_read_scope_override_denied",
                    execution_request,
                    detail={"fields": sorted(_FILE_READ_SCOPE_OVERRIDE_FIELDS.intersection(payload))},
                )
            payload_target = payload.get("target")
            if payload_target is not None and str(payload_target).strip() != target.strip():
                return self._deny(
                    "file_read_scope_override_denied",
                    execution_request,
                    detail={"error": "executor_payload_target_override"},
                )
            payload_action = payload.get("action")
            if payload_action is not None and str(payload_action).strip().lower() != str(tool_def.action).strip().lower():
                return self._deny(
                    "file_read_scope_override_denied",
                    execution_request,
                    detail={"error": "executor_payload_action_override"},
                )

        try:
            normalized_target = self._normalize_file_read_target(
                target=target,
                workspace_root=workspace_root,
                scope_root=scope_root,
            )
        except ValueError as exc:
            return self._deny(
                "file_read_scope_denied",
                execution_request,
                detail={"error": str(exc), "target": target},
            )

        trusted_payload = dict(payload or {})
        trusted_payload["target"] = normalized_target
        trusted_payload["action"] = str(tool_def.action)

        trusted_context = dict(context)
        trusted_context["target"] = normalized_target
        trusted_context["executor_payload"] = trusted_payload
        execution_request["context"] = trusted_context
        return trusted_context

    def _resolve_workspace_root(self) -> Optional[Path]:
        if self._workspace_root is not None:
            return self._workspace_root

        auth_root = getattr(self._execution_authorization, "_root", None)
        if auth_root is not None:
            return Path(auth_root).resolve()

        executor_owner = getattr(self._executor, "__self__", None)
        executor_root = getattr(executor_owner, "_root", None)
        if executor_root is not None:
            return Path(executor_root).resolve()
        return None

    @staticmethod
    def _resolve_scope_root(tool_def: Any, workspace_root: Optional[Path]) -> Optional[Path]:
        if workspace_root is None:
            return None
        input_policy = getattr(tool_def, "input_policy", {})
        scope_root = input_policy.get("scope_root")
        if not isinstance(scope_root, str) or not scope_root.strip():
            return None
        return (workspace_root / scope_root).resolve()

    @staticmethod
    def _contains_scope_override(context: Mapping[str, Any]) -> bool:
        return bool(_FILE_READ_SCOPE_OVERRIDE_FIELDS.intersection(context))

    @staticmethod
    def _normalize_file_read_target(
        *,
        target: str,
        workspace_root: Path,
        scope_root: Path,
    ) -> str:
        raw_target = Path(target.strip())
        resolved = raw_target.resolve() if raw_target.is_absolute() else (workspace_root / raw_target).resolve()
        if not resolved.is_relative_to(scope_root):
            raise ValueError("target_outside_file_read_scope")
        return str(resolved.relative_to(workspace_root)).replace("\\", "/")

    @staticmethod
    def _deny(
        reason: str,
        execution_request: Optional[dict[str, Any]] = None,
        detail: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        return {
            "decision": "DENY",
            "allowed": False,
            "reason": reason,
            "execution_request": execution_request,
            "boundary_result": None,
            "executed": False,
            "result": None,
            "detail": detail or {},
        }
