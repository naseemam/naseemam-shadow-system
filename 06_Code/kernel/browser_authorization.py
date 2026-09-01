"""Browser execution policy subordinate to Ameer's sovereign authority.

Browser actions such as navigate, read, click, fill, screenshot, and wait are
ordinary operational capabilities. This module may validate action shape,
credentials, session state, domain restrictions, and audit evidence, but it may
not create a Founder approval gate.

Founder approval is required only when the browser action itself crosses a
sovereign gate defined by ``kernel.ameer_authority``. Examples: executing an
actual funds movement, or final production activation of a newly-created root
asset. Merely opening a payment page, reading a dashboard, filling a draft form,
or preparing a transaction does not itself move money.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from kernel.ameer_authority import canonical_sovereign_action, requires_founder_approval


class BrowserAction:
    """A browser operation with audit state; not inherently a Founder approval request."""

    VALID_TYPES = {"navigate", "read", "click", "fill", "screenshot", "wait"}

    def __init__(
        self,
        action_type: str,
        target: str,
        description: str,
        expected_result: str,
        parameters: Optional[Dict[str, Any]] = None,
    ):
        if action_type not in self.VALID_TYPES:
            raise ValueError(f"Invalid action type: {action_type}")
        self.id = str(uuid.uuid4())
        self.type = action_type
        self.target = target
        self.description = description
        self.expected_result = expected_result
        self.parameters = parameters or {}
        self.sovereign_action = canonical_sovereign_action(
            self.parameters.get("operation") or action_type,
            self.parameters,
        )
        self.status = "pending_founder" if self.sovereign_action else "authorized"
        self.approval_by = None
        self.approval_at = None
        self.result = None
        self.created_at = datetime.now(timezone.utc).isoformat() + "Z"

    @property
    def requires_founder_approval(self) -> bool:
        return self.sovereign_action is not None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "target": self.target,
            "description": self.description,
            "expected_result": self.expected_result,
            "parameters": self.parameters,
            "status": self.status,
            "sovereign_action": self.sovereign_action,
            "requires_founder_approval": self.requires_founder_approval,
            "approval_by": self.approval_by,
            "approval_at": self.approval_at,
            "result": self.result,
            "created_at": self.created_at,
        }


class BrowserAuthorizationGate:
    """Compatibility API for browser authorization without per-action approval loops.

    Existing callers may continue using propose_action/approve_action/reject_action.
    Ordinary actions are returned already authorized. Only a centrally-defined
    sovereign action receives ``pending_founder``.
    """

    def __init__(self, workspace_root: str | Path):
        self._root = Path(workspace_root).resolve()
        self._ameer_dir = self._root / ".ameer"
        self._state_file = self._ameer_dir / "state.json"

    def propose_action(
        self,
        action_type: str,
        target: str,
        description: str,
        expected_result: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> BrowserAction:
        return BrowserAction(
            action_type=action_type,
            target=target,
            description=description,
            expected_result=expected_result,
            parameters=parameters,
        )

    def requires_approval_for_action(
        self,
        action_type: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> bool:
        safe = parameters or {}
        operation = safe.get("operation") or action_type
        return requires_founder_approval(operation, safe)

    def get_pending_actions(self) -> List[BrowserAction]:
        """Return only legacy/current sovereign browser actions awaiting Founder."""
        try:
            if not self._state_file.exists():
                return []
            with open(self._state_file, "r", encoding="utf-8") as f:
                state = json.load(f)
            pending = state.get("browser_pending_actions", [])
            actions: List[BrowserAction] = []
            for item in pending:
                params = item.get("parameters") or {}
                operation = params.get("operation") or item.get("type")
                if not requires_founder_approval(operation, params):
                    # Legacy per-click/read approval records no longer block Ameer.
                    continue
                action = BrowserAction(
                    action_type=item.get("type"),
                    target=item.get("target"),
                    description=item.get("description"),
                    expected_result=item.get("expected_result"),
                    parameters=params,
                )
                action.id = item.get("id", action.id)
                action.status = "pending_founder"
                actions.append(action)
            return actions
        except Exception:
            return []

    def approve_action(self, action_id: str, approved_by: str = "Naseem") -> bool:
        """Resolve a persisted sovereign browser action; ordinary actions need no call."""
        try:
            if not self._state_file.exists():
                return False
            with open(self._state_file, "r", encoding="utf-8") as f:
                state = json.load(f)
            pending = state.get("browser_pending_actions", [])
            changed = False
            for action in pending:
                if action.get("id") != action_id:
                    continue
                params = action.get("parameters") or {}
                operation = params.get("operation") or action.get("type")
                if not requires_founder_approval(operation, params):
                    # Do not legitimize a legacy invented gate. Mark it migrated.
                    action["status"] = "authorized_by_delegated_policy"
                    action["migration_reason"] = "legacy_browser_gate_removed"
                else:
                    action["status"] = "approved"
                    action["approval_by"] = approved_by
                    action["approval_at"] = datetime.now(timezone.utc).isoformat() + "Z"
                changed = True
                break
            if changed:
                self._ameer_dir.mkdir(parents=True, exist_ok=True)
                with open(self._state_file, "w", encoding="utf-8") as f:
                    json.dump(state, f, indent=2, ensure_ascii=False)
            return changed
        except Exception:
            return False

    def reject_action(self, action_id: str, reason: str = "") -> bool:
        """Reject a persisted sovereign browser action."""
        try:
            if not self._state_file.exists():
                return False
            with open(self._state_file, "r", encoding="utf-8") as f:
                state = json.load(f)
            pending = state.get("browser_pending_actions", [])
            for action in pending:
                if action.get("id") != action_id:
                    continue
                params = action.get("parameters") or {}
                operation = params.get("operation") or action.get("type")
                if not requires_founder_approval(operation, params):
                    return False
                action["status"] = "rejected"
                action["rejection_reason"] = reason
                action["rejection_at"] = datetime.now(timezone.utc).isoformat() + "Z"
                self._ameer_dir.mkdir(parents=True, exist_ok=True)
                with open(self._state_file, "w", encoding="utf-8") as f:
                    json.dump(state, f, indent=2, ensure_ascii=False)
                return True
            return False
        except Exception:
            return False
