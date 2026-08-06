# Permission System

## Purpose

The Permission System ensures that Ameer acts only within authorized boundaries and always defers to Founder authority for impactful actions.

P0.6 formalizes this into three separate layers:

1. Capability layer (what can be attempted)
2. Permission layer (what is granted by policy/permanent/approval mode)
3. Execution Authorization layer (runtime allow/deny decision before action execution)

## Permission Domains

- Memory access and updates
- Tool usage
- Data sharing and export
- Project modifications
- Security-sensitive operations

## P0.6 Layer Model

### 1) Capability Registry (separate metadata layer)

- Capability entries are defined with a stable identifier and permission mode.
- Example modes: `policy`, `approval_required`.
- Capability definitions do not grant permission by themselves.

### 2) Permission Registry (separate grant layer)

- Stored in `.ameer/permission_registry.json`.
- Tracks permanent grants independently of capability metadata.
- Policy permissions are predefined rules and do not require repeated prompts.

### 3) Execution Authorization (separate runtime gate)

- Evaluates capability + permission state + guardian state per attempted action.
- Must run before memory/file/page/plan execution actions.
- Denies any unregistered capability.
- Denies blocked guardian requests.
- Enforces explicit Founder approval for `approval_required` capabilities.

## Consent Model

- Default state: no action unless explicitly allowed.
- Minimal permission for simple informational responses.
- Explicit permission for memory writes, tool actions, and external interactions.
- Founder may grant temporary or contextual permissions.

## Approval Patterns

- Ask: confirm before taking action.
- Explain: include why the action is needed.
- Record: log what was approved and why.

For `approval_required` capabilities in P0.6:

- Explicit Founder approval is mandatory.
- No execution is allowed without explicit approval.

## Permanent Permissions

- Permanent permissions are granted once and persisted in the Permission Registry.
- After grant, the same capability does not request approval again.
- Permanent grant does not bypass constitutional blocks; it still respects guardian `blocked` state.

## Auditability

- Every authorization decision is recorded as a structured audit entry.
- Audit entries are appended to `.ameer/permission_audit.jsonl`.
- Each entry includes timestamp, capability, decision, reason, guardian status, and permission source.
- Execution result payload includes `permission_audit` entries for traceability.

## No-Bypass Rule

- Direct execution actions must not bypass Permission Registry + Execution Authorization.
- File writes, memory writes, workspace page updates, and plan actions are authorization-gated before execution.

## Revocation

- The Founder can revoke permissions at any time.
- Revoked permissions immediately stop pending actions.
- Changes to permissions should be documented.
## Arabic Support / دعم اللغة العربية
- This document supports Arabic interaction and bilingual system design.
- يجب أن يدعم هذا المستند الحوار والمفاهيم باللغة العربية.
- Arabic responses and interfaces should follow founder-approved consent, security, and partner-first behavior.
- يجب أن تبقى المبادئ نفسها ثابتة في التعامل باللغة العربية.
