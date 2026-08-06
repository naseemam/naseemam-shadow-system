# Changelog

## v1.0.0-P0.6-Executive-Capability-Governance (2026-08-06)
### Added
- `CapabilityRegistry` (`06_Code/kernel/capability_registry.py`): Capability Manifest with 6 lifecycle states (core/extended/experimental/suspended/deprecated/retired), Capability Card schema, Conflict Detection, and permanent archive policy (no deletions). Seeded with 6 sealed core capabilities. Stored in `.ameer/capabilities.json`.
- `PermissionRegistry` (`06_Code/kernel/permission_registry.py`): Separates capability ownership from execution permission. Each capability has a Permission Card with owned/enabled/permission_status/scope/granted_by/granted_at/expires_at. Full audit log. Stored in `.ameer/permissions.json`.
- `ExecutionAuthorization` (`06_Code/kernel/execution_authorization.py`): Per-action runtime authorization gate. Checks capability status → permission status → issues approved/denied/pending result. Founder can authorize or deny pending requests. Full execution log. Stored in `.ameer/execution_auth.json`.
- `ExecutiveKernel` now boots all three P0.6 components (capability_registry, permission_registry, execution_authorization) and reports them in health.
- `before_request` returns `capability_governance` snapshot and `pending_execution_requests`.
- `health()` now includes `active_capabilities` (counts by status) and `pending_execution_requests`.
- `03_Architecture/Executive_Capability_Governance.md`: Full P0.6 architecture document covering all 7 layers, governance principle, capability evolution pipeline, risk register, and rollback plan.
- ADR-008 in `01_Governance/ADR.md` documenting the Executive Capability Governance decision.
- `07_Tests/test_p06_capability_governance.py`: 39 new acceptance tests covering CapabilityRegistry, PermissionRegistry, ExecutionAuthorization, and ExecutiveKernel integration.

### Architecture
The complete P0.6 governance stack:
```
Capability Registry  →  Permission Registry  →  Execution Authorization  →  Action
```
Capabilities are permanent; permissions are independent; each execution requires runtime authorization.
Founder approval is required at every stage of capability expansion.

## v1.0.0-P0.4-Executive-Activation (2026-08-05)
### Added
- `DecisionEngine` (`06_Code/kernel/decision_engine.py`): persistent decision log with record/update/pending/recent API. Stored in `.ameer/decisions.json`.
- `ApprovalGate` (`06_Code/kernel/approval_gate.py`): approval flow for high-impact actions (delete, publish, external, financial). Stored in `.ameer/approvals.json`.
- `ExecutiveKernel` now boots `DecisionEngine` and `ApprovalGate` (reported as components in health).
- `before_request` returns `pending_approval_requests` and `proactive_briefing` (first-turn only).
- `_build_proactive_briefing()` — generates a startup briefing with active projects, pending approvals, pending decisions, running tasks.
- `record_decision()` / `request_approval()` helper methods on `ExecutiveKernel`.
- `/decisions` GET/POST endpoints.
- `/approvals` GET/POST endpoints.
- `/approvals/{id}/approve` and `/approvals/{id}/reject` POST endpoints.
- `utf8_json_response` now accepts optional `status_code` parameter.
- `07_Tests/test_p04_executive_activation.py`: 53 new acceptance tests for all P0.4 features.

### Changed
- `ExecutiveKernel.health()` now includes `pending_decisions` and `pending_approval_requests` counts.
- Kernel boot sequence now initializes 6 components (added decision_engine, approval_gate).

## v0.3-architecture-freeze (2026-08-02)
### Added
- Architecture baseline document for the current runtime and orchestration structure.
- A clear version marker to anchor future work before LLM-related expansion.

### Changed
- Development diagnostics and temporary manual-test utilities are now expected to live under [08_DevTools](08_DevTools).

### Notes
- This baseline preserves the existing runtime surface and avoids functional changes while establishing a stable reference point.
