"""
browser_authorization.py
========================
Browser Action Authorization Model

Every browser action follows this pipeline:
  1. Ameer plans the action (navigate, read, click, fill form)
  2. Ameer displays: action description + expected result
  3. Founder reviews in chat and approves/rejects
  4. Only approved actions execute
  5. Result is reported back to founder

This ensures founder (Naseem) has final say on all browser interactions.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, List


class BrowserAction:
    """A single browser action pending founder approval."""
    
    VALID_TYPES = {"navigate", "read", "click", "fill", "screenshot", "wait"}
    
    def __init__(
        self,
        action_type: str,
        target: str,
        description: str,
        expected_result: str,
        parameters: Optional[Dict[str, Any]] = None,
    ):
        self.id = str(uuid.uuid4())
        self.type = action_type
        self.target = target
        self.description = description
        self.expected_result = expected_result
        self.parameters = parameters or {}
        self.status = "pending_approval"  # pending_approval → approved → executed
        self.approval_by = None
        self.approval_at = None
        self.result = None
        self.created_at = datetime.now(timezone.utc).isoformat() + "Z"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "target": self.target,
            "description": self.description,
            "expected_result": self.expected_result,
            "parameters": self.parameters,
            "status": self.status,
            "approval_by": self.approval_by,
            "approval_at": self.approval_at,
            "result": self.result,
            "created_at": self.created_at,
        }


class BrowserAuthorizationGate:
    """
    Central gate for all browser actions.
    
    Requires founder (Naseem) explicit approval before any browser interaction.
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
        """Create a proposed browser action and return it for founder approval."""
        
        if action_type not in BrowserAction.VALID_TYPES:
            raise ValueError(f"Invalid action type: {action_type}")
        
        action = BrowserAction(
            action_type=action_type,
            target=target,
            description=description,
            expected_result=expected_result,
            parameters=parameters,
        )
        
        return action
    
    def get_pending_actions(self) -> List[BrowserAction]:
        """Get all browser actions awaiting founder approval."""
        try:
            if not self._state_file.exists():
                return []
            
            with open(self._state_file, 'r', encoding='utf-8') as f:
                state = json.load(f)
            
            pending = state.get("browser_pending_actions", [])
            actions = []
            for item in pending:
                action = BrowserAction(
                    action_type=item.get("type"),
                    target=item.get("target"),
                    description=item.get("description"),
                    expected_result=item.get("expected_result"),
                    parameters=item.get("parameters"),
                )
                action.id = item.get("id", action.id)
                action.status = item.get("status", "pending_approval")
                actions.append(action)
            
            return actions
        except Exception:
            return []
    
    def approve_action(self, action_id: str, approved_by: str = "Naseem") -> bool:
        """Founder approves a browser action."""
        try:
            if not self._state_file.exists():
                return False
            
            with open(self._state_file, 'r', encoding='utf-8') as f:
                state = json.load(f)
            
            pending = state.get("browser_pending_actions", [])
            for action in pending:
                if action.get("id") == action_id:
                    action["status"] = "approved"
                    action["approval_by"] = approved_by
                    action["approval_at"] = datetime.now(timezone.utc).isoformat() + "Z"
                    break
            
            with open(self._state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception:
            return False
    
    def reject_action(self, action_id: str, reason: str = "") -> bool:
        """Founder rejects a browser action."""
        try:
            if not self._state_file.exists():
                return False
            
            with open(self._state_file, 'r', encoding='utf-8') as f:
                state = json.load(f)
            
            pending = state.get("browser_pending_actions", [])
            for action in pending:
                if action.get("id") == action_id:
                    action["status"] = "rejected"
                    action["rejection_reason"] = reason
                    action["rejection_at"] = datetime.now(timezone.utc).isoformat() + "Z"
                    break
            
            with open(self._state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception:
            return False
