"""
authorization_framework.py
==========================
Complete Authorization Framework for Ameer

Operations categorized by delegated authority:
- Existing assets: execute immediately after capability and scope validation.
- New root site/program/system/repository: requires founder approval before creation.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional, List

from kernel.ameer_authority import requires_founder_approval


class OperationType(Enum):
    """Operation classification."""
    LOCAL = "local"
    EXTERNAL = "external"
    DEPLOYMENT = "deployment"
    DESTRUCTIVE = "destructive"


class ApprovalLevel(Enum):
    """Approval requirement."""
    NONE = "none"
    FOUNDER = "founder"


class ResourceType(Enum):
    """Resource categories."""
    FILES = "files"
    BROWSER = "browser"
    GITHUB = "github"
    EMAIL = "email"
    GOOGLE = "google"
    SLACK = "slack"
    RAILWAY = "railway"
    API = "api"
    DATABASE = "database"
    SHELL = "shell"


# Authorization Matrix
AUTHORIZATION_MATRIX = {
    # Local Operations - No approval
    (ResourceType.FILES, OperationType.LOCAL): ApprovalLevel.NONE,
    (ResourceType.SHELL, OperationType.LOCAL): ApprovalLevel.NONE,
    # Executive integrations - no founder approval in this policy. Each connector
    # remains bounded by its own scope and audit trail.
    (ResourceType.BROWSER, OperationType.EXTERNAL): ApprovalLevel.NONE,
    (ResourceType.GITHUB, OperationType.EXTERNAL): ApprovalLevel.NONE,
    (ResourceType.EMAIL, OperationType.EXTERNAL): ApprovalLevel.NONE,
    (ResourceType.GOOGLE, OperationType.EXTERNAL): ApprovalLevel.NONE,
    (ResourceType.SLACK, OperationType.EXTERNAL): ApprovalLevel.NONE,
    (ResourceType.API, OperationType.EXTERNAL): ApprovalLevel.NONE,
    # Deployment and destructive actions remain delegated when they operate
    # inside an existing approved asset. Root-asset creation is evaluated from
    # the action and context by the central authority policy.
}


class PendingOperation:
    """Operation awaiting founder approval."""
    
    def __init__(
        self,
        resource_type: ResourceType,
        operation_type: OperationType,
        action: str,
        description: str,
        expected_result: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.id = str(uuid.uuid4())
        self.resource_type = resource_type
        self.operation_type = operation_type
        self.action = action
        self.description = description
        self.expected_result = expected_result
        self.details = details or {}
        self.status = "pending"
        self.approved_by = None
        self.approved_at = None
        self.created_at = datetime.now(timezone.utc).isoformat() + "Z"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "resource_type": self.resource_type.value,
            "operation_type": self.operation_type.value,
            "action": self.action,
            "description": self.description,
            "expected_result": self.expected_result,
            "details": self.details,
            "status": self.status,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at,
            "created_at": self.created_at,
        }


class AuthorizationFramework:
    """Central authorization gate for all Ameer operations."""
    
    def __init__(self, workspace_root: str | Path):
        self._root = Path(workspace_root).resolve()
        self._ameer_dir = self._root / ".ameer"
        self._state_file = self._ameer_dir / "state.json"
    
    def check_approval_needed(
        self,
        resource_type: ResourceType,
        operation_type: OperationType,
        action: str = "",
        context: Optional[Dict[str, Any]] = None,
    ) -> ApprovalLevel:
        """Check the only founder gate: creation of a new root asset."""
        if requires_founder_approval(action, context):
            return ApprovalLevel.FOUNDER
        return ApprovalLevel.NONE
    
    def propose_operation(
        self,
        resource_type: ResourceType,
        operation_type: OperationType,
        action: str,
        description: str,
        expected_result: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> PendingOperation:
        """Propose an operation and check if approval needed."""
        approval_needed = self.check_approval_needed(
            resource_type,
            operation_type,
            action=action,
            context=details,
        )
        
        op = PendingOperation(
            resource_type=resource_type,
            operation_type=operation_type,
            action=action,
            description=description,
            expected_result=expected_result,
            details=details,
        )
        
        # If no approval needed, auto-approve
        if approval_needed == ApprovalLevel.NONE:
            op.status = "approved"
            op.approved_by = "system"
            op.approved_at = datetime.now(timezone.utc).isoformat() + "Z"
        
        return op
    
    def approve_operation(self, operation_id: str, approved_by: str = "Naseem") -> bool:
        """Founder approves an operation."""
        try:
            if not self._state_file.exists():
                return False
            
            with open(self._state_file, 'r', encoding='utf-8') as f:
                state = json.load(f)
            
            pending = state.get("pending_operations", [])
            for op in pending:
                if op.get("id") == operation_id:
                    op["status"] = "approved"
                    op["approved_by"] = approved_by
                    op["approved_at"] = datetime.now(timezone.utc).isoformat() + "Z"
                    break
            
            with open(self._state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception:
            return False
    
    def reject_operation(self, operation_id: str, reason: str = "") -> bool:
        """Founder rejects an operation."""
        try:
            if not self._state_file.exists():
                return False
            
            with open(self._state_file, 'r', encoding='utf-8') as f:
                state = json.load(f)
            
            pending = state.get("pending_operations", [])
            for op in pending:
                if op.get("id") == operation_id:
                    op["status"] = "rejected"
                    op["rejection_reason"] = reason
                    break
            
            with open(self._state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception:
            return False
