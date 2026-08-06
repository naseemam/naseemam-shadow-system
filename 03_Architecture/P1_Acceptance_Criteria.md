# P1 Acceptance Criteria

## Purpose

This document defines completion criteria for each P1 phase.
A phase is not complete unless all listed acceptance criteria are satisfied.

P1 scope is runtime delivery only.
P0.6 governance remains frozen except for real bug fixes.

## Global P1 Gates

These gates apply to every P1 phase:

- Architecture contracts are respected (`P1_Runtime_Contracts.md`).
- No redesign of ExecutiveKernel/ExecutiveBrain governance.
- Unit tests exist for new behavior and pass.
- Regression checks for affected runtime paths pass.
- Approval boundary remains policy-driven (ask only when required).

## P1.1 Runtime State

A phase is complete only if:

- Runtime state persists between tasks in the same run.
- Runtime state is restored after server restart.
- Active task list is not lost across reload.
- State includes required fields from runtime contract.
- All runtime_state unit tests pass.

## P1.2 Task Scheduler

A phase is complete only if:

- Tasks are ordered by dependencies and priority.
- Cycles are detected and blocked.
- Approval-required task cannot execute before approval state is granted.
- Scheduler supports serial and parallel-safe modes.
- All scheduler unit tests pass.

## P1.3 Validate Plan

A phase is complete only if:

- Validation blocks missing dependencies.
- Validation blocks forbidden or policy-violating actions.
- Validation blocks resource-unavailable tasks.
- Validation reports conflicts (write target/order/lock).
- All validation unit tests pass.

## P1.4 Execution Engine (File Executor First)

A phase is complete only if:

- Executor interface contract is implemented.
- File executor can create/update/read within sandbox workspace only.
- Execution returns `ExecutionResult` contract shape.
- Failures are captured as structured errors without crashing runtime.
- All file executor unit tests pass.

## P1.5 /execute Endpoint

A phase is complete only if:

- `/execute` routes through same ExecutiveKernel used by `/ask`.
- No split-brain runtime path is introduced.
- Endpoint returns stable run/report identifiers.
- Approval-required tasks return explicit pending-approval status.
- Endpoint tests pass.

## P1.6 First End-to-End Task

Target first E2E command:

- "أنشئ صفحة HTML"

A phase is complete only if:

- Full lifecycle runs: Parse -> Plan -> Validate Plan -> Schedule -> Execute -> Verify -> Reflect -> Report.
- Execution writes only to sandbox workspace: `09_Assets/runtime_workspace/`.
- Report is generated in `ExecutionReport` schema.
- No prohibited actions are executed.
- End-to-end test passes.

## P1.7 Git Integration (After E2E HTML Success)

A phase is complete only if:

- Git stage/commit occur only after Verify success.
- Commit is skipped when verify fails.
- Commit metadata links to run/report ID.
- Git integration tests pass.

## P1.8 Preview and Additional Executors

A phase is complete only if:

- Preview executor/service is added without changing governance model.
- New executors are added by interface implementation, not if/else sprawl.
- Railway/Cloudflare/Supabase integrations follow executor contract.
- Integration tests for each added executor pass.

## Arabic Support / دعم اللغة العربية

- This document supports Arabic interaction and bilingual system design.
- يجب أن يدعم هذا المستند الحوار والمفاهيم باللغة العربية.
- Arabic responses and interfaces should follow founder-approved consent, security, and partner-first behavior.
- يجب أن تبقى المبادئ نفسها ثابتة في التعامل باللغة العربية.
