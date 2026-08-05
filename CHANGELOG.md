# Changelog

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
