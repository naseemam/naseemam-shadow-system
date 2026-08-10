from __future__ import annotations

from typing import Any, Mapping, Optional


_REGISTRY_OWNED_FIELDS = frozenset(
    {"capability", "capability_name", "action", "risk_level", "approval_required"}
)


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
    ) -> None:
        self._tool_registry = tool_registry
        self._execution_boundary = execution_boundary
        self._execution_authorization = execution_authorization
        self._approval_gate = approval_gate
        self._executor = executor

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

        try:
            boundary_result = evaluate_fn(
                guardian=dict(guardian),
                request_type=request_type,
                intent=intent,
                capability_name=capability_name,
                action=action,
                context={
                    **sanitized_context,
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
