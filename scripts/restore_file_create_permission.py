#!/usr/bin/env python3
"""
restore_file_create_permission.py
==================================
ONE-TIME restoration script.

Purpose
-------
The Production `/app/.ameer/permissions.json` volume lost the "file.create"
permission card that exists in GitHub main (granted 2026-08-10T18:38:44Z by
Naseem, scope_root="09_Assets/runtime_workspace", action="write"). As a
result, `ExecutionAuthorization.check()` cannot locate the "file.create"
permission when `TaskDecomposer` requests it, and file-creation execution
requests are denied.

This script re-grants ONLY the "file.create" permission using
`PermissionRegistry.grant()`, exactly matching the GitHub main
source-of-truth values. It does NOT touch any other permission card
(file.read / file_operations, shell.run / shell_execution), does not modify
the audit_log beyond the single append that `PermissionRegistry.grant()`
itself performs, and does not change any capability UUIDs.

Run once, manually:
    python scripts/restore_file_create_permission.py

After Production state is confirmed to match GitHub main, this script can be
safely deleted. It contains no startup hooks and is NOT imported by
`ameer_server.py` or any kernel module.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# ─── Make 06_Code importable, exactly like ameer_server.py does ───────────────
_REPO_ROOT = Path(__file__).resolve().parent.parent
_CODE_ROOT = str(_REPO_ROOT / "06_Code")
if _CODE_ROOT not in sys.path:
    sys.path.insert(0, _CODE_ROOT)

from kernel.permission_registry import PermissionRegistry  # noqa: E402


# ─── Restoration target — must match GitHub main exactly ──────────────────────
CAPABILITY_ID = "file.create"
GRANTED_BY = "Naseem"
SCOPE = {
    "action": "write",
    "scope_kind": "runtime_workspace_only",
    "scope_root": "09_Assets/runtime_workspace",
    "tool_name": "file.create",
}


def _resolve_workspace_root() -> Path:
    """
    Resolve the workspace root the same way ameer_runtime.resolve_data_root()
    does, so this script targets the exact same .ameer/permissions.json file
    that ExecutionAuthorization reads from at runtime.
    """
    try:
        from ameer_runtime import resolve_data_root  # noqa: E402

        return Path(resolve_data_root()).resolve()
    except Exception:
        # Fallback: honour AMEER_DATA_DIR directly, else default to repo root
        # (matches production convention of workspace root = /app).
        raw = os.getenv("AMEER_DATA_DIR", "").strip()
        if raw:
            data_dir = Path(raw).resolve()
            if data_dir.name == ".ameer":
                return data_dir.parent
            return data_dir
        return _REPO_ROOT


def main() -> int:
    workspace_root = _resolve_workspace_root()
    permissions_path = workspace_root / ".ameer" / "permissions.json"

    print("=" * 72)
    print("Restoring lost permission: file.create")
    print("=" * 72)
    print(f"Workspace root      : {workspace_root}")
    print(f"Permissions file    : {permissions_path}")
    print()

    registry = PermissionRegistry(workspace_root)

    # Capture pre-restoration state (for visibility only — not modified here).
    existing_card = registry.get_for_capability(CAPABILITY_ID)
    if existing_card is None:
        print("Pre-restoration state: no permission card found for 'file.create'.")
    else:
        print(
            "Pre-restoration state: "
            f"permission_status={existing_card.get('permission_status')!r}"
        )
    print()

    # ── Grant ONLY the file.create permission, matching GitHub main values ────
    scope_json = json.dumps(SCOPE, ensure_ascii=False, sort_keys=True)
    permission_id = registry.grant(
        capability_id=CAPABILITY_ID,
        scope=scope_json,
        granted_by=GRANTED_BY,
    )

    # ── Verify the card was created/updated correctly ──────────────────────────
    restored_card = registry.get_for_capability(CAPABILITY_ID)
    if restored_card is None:
        print("ERROR: Permission card not found after grant(). Restoration failed.")
        return 1

    status = restored_card.get("permission_status")
    if status != "granted":
        print(
            f"ERROR: Expected permission_status='granted', got {status!r}. "
            "Restoration failed."
        )
        return 1

    # ── Verify persistence to disk ──────────────────────────────────────────────
    persisted_ok = permissions_path.exists()
    persisted_card = None
    if persisted_ok:
        try:
            on_disk = json.loads(permissions_path.read_text(encoding="utf-8"))
            for card in on_disk.get("permissions", []):
                if card.get("capability_id") == CAPABILITY_ID:
                    persisted_card = card
                    break
        except (OSError, json.JSONDecodeError):
            persisted_ok = False

    persisted_ok = persisted_ok and persisted_card is not None and (
        persisted_card.get("permission_status") == "granted"
    )

    # ── Report ──────────────────────────────────────────────────────────────────
    print("-" * 72)
    print("RESTORATION RESULT")
    print("-" * 72)
    print(f"Permission ID       : {restored_card.get('permission_id')}")
    print(f"Capability ID       : {restored_card.get('capability_id')}")
    print(f"Status              : {restored_card.get('permission_status')}")
    print(f"Owned               : {restored_card.get('owned')}")
    print(f"Enabled             : {restored_card.get('enabled')}")
    print(f"Granted by          : {restored_card.get('granted_by')}")
    print(f"Granted at          : {restored_card.get('granted_at')}")
    print(f"Scope (parsed)      : {json.dumps(SCOPE, ensure_ascii=False, indent=2)}")
    print(f"Scope (stored raw)  : {restored_card.get('scope')}")
    print()
    print(f"Persisted to disk   : {persisted_ok}")
    print(f"Permissions file    : {permissions_path}")
    print("-" * 72)

    if status == "granted" and persisted_ok:
        print("SUCCESS: 'file.create' permission restored and persisted.")
        print(
            "This script is safe to remove now that Production state matches "
            "GitHub main."
        )
        return 0

    print("FAILURE: restoration could not be fully verified.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
