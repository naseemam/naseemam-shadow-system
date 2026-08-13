from __future__ import annotations

import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Optional

from kernel.shell_external_effect_classifier import ShellExternalEffectClassifier


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


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

        policy_result = self._enforce_tool_policy(tool_name, tool_def, sanitized_context, execution_request, requested_by)
        if isinstance(policy_result, dict) and policy_result.get("decision") == "DENY":
            if tool_name == "shell.run":
                self._emit_shell_audit(tool_name, sanitized_context, policy_result)
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
            if tool_name == "shell.run":
                self._emit_shell_audit(tool_name, sanitized_context, result)
            return result

        execute_fn = self._resolve_executor(tool_name)
        if not callable(execute_fn):
            return self._deny("executor_unavailable", execution_request)
        payload = validated_context.get("executor_payload", validated_context)
        try:
            execution_result = execute_fn(payload)
        except Exception as exc:
            failed_result = {
                **result,
                "decision": "DENY",
                "allowed": False,
                "reason": "executor_unavailable",
                "detail": {"error": str(exc)},
            }
            if tool_name == "shell.run":
                self._emit_shell_audit(tool_name, sanitized_context, failed_result)
            return failed_result
        result["executed"] = True
        result["result"] = execution_result
        if tool_name == "shell.run":
            self._emit_shell_audit(tool_name, sanitized_context, result)
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
        requested_by: str = "executive_kernel",
    ) -> Optional[Mapping[str, Any] | dict[str, Any]]:
        if tool_name == "file.read":
            return self._enforce_file_read_policy(tool_def, context, execution_request)
        if tool_name == "file.create":
            return self._enforce_file_create_policy(tool_def, context, execution_request)
        if tool_name == "shell.run":
            return self._enforce_shell_run_policy(tool_def, context, execution_request, requested_by)
        return None

    def _enforce_shell_run_policy(
        self,
        tool_def: Any,
        context: Mapping[str, Any],
        execution_request: dict[str, Any],
        requested_by: str = "executive_kernel",
    ) -> Mapping[str, Any] | dict[str, Any]:
        """Validate shell.run context; enforce external-effect approval policy."""
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

        # ── External-effect enforcement ────────────────────────────────────
        # The ToolRegistry declares `approval_required_for_external_effects: True`
        # in the shell.run input_policy.  This block makes that declaration
        # an actual enforcement decision — not just metadata.
        requires_ext_approval = bool(
            getattr(tool_def, "input_policy", {}).get(
                "approval_required_for_external_effects", False
            )
        )
        if requires_ext_approval:
            classification = ShellExternalEffectClassifier.classify(command)
            if classification["is_external_effect"]:
                if self._approval_gate is None:
                    return self._deny(
                        "approval_gate_required_for_external_effect",
                        execution_request,
                        detail={"command_classification": classification},
                    )
                # Caller may supply a pre-approved approval_id in context.
                approval_id = context.get("approval_id")
                if approval_id:
                    is_approved_fn = getattr(self._approval_gate, "is_approved", None)
                    if callable(is_approved_fn) and is_approved_fn(approval_id):
                        # Pre-verified — annotate trusted context and proceed.
                        pass  # fall through to build trusted_context below
                    else:
                        return {
                            **self._deny(
                                "external_effect_approval_not_verified",
                                execution_request,
                                detail={
                                    "approval_id": approval_id,
                                    "command_classification": classification,
                                },
                            ),
                            "status": "approval_required",
                            "approval_required": True,
                            "approval_id": approval_id,
                        }
                else:
                    # No prior approval — create approval request and block.
                    request_fn = getattr(self._approval_gate, "request", None)
                    if callable(request_fn):
                        new_approval_id = request_fn(
                            action="external",
                            description=(
                                f"shell.run external-effect command: "
                                f"{classification['command_root']!r}"
                            ),
                            requested_by=requested_by,
                            context={
                                "command_root": classification["command_root"],
                                "subcommand": classification["subcommand"],
                                "tool_name": "shell.run",
                            },
                        )
                    else:
                        new_approval_id = None
                    return {
                        **self._deny(
                            "approval_required",
                            execution_request,
                            detail={
                                "command_classification": classification,
                                "approval_id": new_approval_id,
                            },
                        ),
                        "status": "approval_required",
                        "approval_required": True,
                        "approval_id": new_approval_id,
                    }
        # ── End external-effect enforcement ───────────────────────────────

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

    # ── Audit / Trace ────────────────────────────────────────────────────────

    def _emit_shell_audit(
        self,
        tool_name: str,
        context: Mapping[str, Any],
        result: dict[str, Any],
    ) -> None:
        """
        Write a structured audit record for every shell.run dispatch attempt.

        Every record contains:
        - request_id / execution_id
        - tool_name
        - command or command_classification
        - authorization_result (ALLOW / DENY / PENDING)
        - approval_required
        - approval_status
        - execution_result summary
        - timestamp

        Records are appended to .ameer/shell_audit.jsonl (one JSON object per
        line) inside the workspace root so they survive restarts.  If the
        workspace root is unknown the record is emitted to stderr only — it is
        *never* silently dropped.
        """
        command = context.get("command", "")
        classification = ShellExternalEffectClassifier.classify(command) if command else {
            "is_external_effect": False,
            "command_root": "",
            "subcommand": "",
            "reason": "empty_command",
        }

        # Derive approval fields from policy_result embedded in result.
        approval_required: bool = bool(result.get("approval_required", False))
        approval_status: str = "n/a"
        approval_id = result.get("approval_id")

        policy_detail = result.get("detail") or {}
        if result.get("status") == "approval_required" or approval_required:
            approval_status = "pending"
        elif result.get("decision") == "ALLOW" and result.get("executed"):
            approval_status = "approved" if approval_required else "not_required"
        elif result.get("decision") == "DENY":
            if approval_required:
                approval_status = "denied_no_approval"
            else:
                approval_status = "denied"

        # If the approval_gate has an approval_id, look up its status.
        if approval_id and self._approval_gate is not None:
            is_approved_fn = getattr(self._approval_gate, "is_approved", None)
            if callable(is_approved_fn):
                try:
                    if is_approved_fn(approval_id):
                        approval_status = "approved"
                except Exception:
                    pass

        execution_id = str(uuid.uuid4())

        record: dict[str, Any] = {
            "execution_id": execution_id,
            "request_id": (
                (result.get("execution_request") or {}).get("request_id")
                or approval_id
                or execution_id
            ),
            "tool_name": tool_name,
            "command": command if isinstance(command, str) else json.dumps(command),
            "command_classification": {
                "is_external_effect": classification.get("is_external_effect"),
                "command_root": classification.get("command_root"),
                "subcommand": classification.get("subcommand"),
                "reason": classification.get("reason"),
            },
            "authorization_result": result.get("decision", "DENY"),
            "approval_required": approval_required,
            "approval_id": approval_id,
            "approval_status": approval_status,
            "execution_result": (
                result.get("result") if result.get("executed") else None
            ),
            "executed": bool(result.get("executed")),
            "reason": result.get("reason", ""),
            "timestamp": _now_iso(),
        }

        line = json.dumps(record, default=str, ensure_ascii=False)

        # Persist to audit log file.
        workspace_root = self._workspace_root
        if workspace_root is not None:
            audit_dir = workspace_root / ".ameer"
            try:
                audit_dir.mkdir(parents=True, exist_ok=True)
                audit_path = audit_dir / "shell_audit.jsonl"
                with open(audit_path, "a", encoding="utf-8") as fh:
                    fh.write(line + "\n")
            except Exception as exc:
                print(f"[ToolDispatcher] shell audit write error: {exc}", file=sys.stderr)

        # Always emit to stderr as secondary trace.
        print(f"[shell_audit] {line}", file=sys.stderr)

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
