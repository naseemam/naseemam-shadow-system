# P1 Runtime Contracts

## Purpose

This document defines the data contracts for P1 Executive Runtime.
It is contract-only and does not define implementation details.

P0.6 governance remains the authority layer.
P1 adds runtime execution capability on top of that stable base.

## Kernel Path Contract

Both runtime entry points must use the same kernel path:

- /ask -> ExecutiveKernel -> ExecutiveBrain (conversation or execution by intent)
- /execute -> ExecutiveKernel -> ExecutiveBrain (execution path)

No split-brain runtime is allowed.

## Runtime Lifecycle Contract

1. Parse
2. Plan
3. Validate Plan
4. Schedule
5. Execute
6. Verify
7. Reflect
8. Report

## Object Contracts

### Task

Represents one planned action before validation.

```json
{
  "id": "task-001",
  "action": "create_file",
  "target": "09_Assets/web/pages/home/index.html",
  "executor": "file",
  "inputs": {
    "content": "<html></html>"
  },
  "approval_required": false,
  "dependencies": [],
  "priority": 50,
  "metadata": {
    "source": "task_decomposer",
    "created_at": "2026-08-07T00:00:00Z"
  }
}
```

Required fields:

- id
- action
- executor
- approval_required
- dependencies
- priority

### ValidatedTask

Task after policy, dependency, and resource checks.

```json
{
  "task": "<Task>",
  "is_valid": true,
  "blocked": false,
  "approval_state": "not_required",
  "validation_errors": [],
  "validation_warnings": [],
  "resource_requirements": {
    "network": false,
    "filesystem": true,
    "tools": ["file"]
  }
}
```

Required fields:

- task
- is_valid
- blocked
- approval_state
- validation_errors

approval_state values:

- not_required
- required_pending
- required_granted
- denied

### ScheduledTask

Validated task with scheduling decisions.

```json
{
  "task": "<ValidatedTask>",
  "queue": "default",
  "run_mode": "parallel_safe",
  "order": 3,
  "batch_id": "batch-01",
  "scheduled_after": ["task-000"],
  "scheduled_at": "2026-08-07T00:00:10Z"
}
```

Required fields:

- task
- queue
- run_mode
- order

run_mode values:

- serial
- parallel_safe

### ExecutionResult

Output of one executor task run.

```json
{
  "task_id": "task-001",
  "executor": "file",
  "status": "succeeded",
  "started_at": "2026-08-07T00:00:11Z",
  "finished_at": "2026-08-07T00:00:12Z",
  "outputs": {
    "path": "09_Assets/web/pages/home/index.html"
  },
  "artifacts": [],
  "errors": [],
  "warnings": []
}
```

Required fields:

- task_id
- executor
- status
- started_at
- finished_at

status values:

- succeeded
- failed
- blocked
- skipped
- cancelled

### ExecutionReport

Final runtime report after verify and reflection.

```json
{
  "run_id": "run-20260807-0001",
  "goal": "create one HTML page",
  "status": "completed",
  "summary": "1 task succeeded, 0 failed",
  "totals": {
    "tasks": 1,
    "succeeded": 1,
    "failed": 0,
    "blocked": 0,
    "cancelled": 0
  },
  "results": ["<ExecutionResult>"],
  "verification": {
    "passed": true,
    "checks": ["file_exists", "html_lint"]
  },
  "reflection": {
    "issues": [],
    "improvements": [],
    "refactors": [],
    "risks": []
  },
  "approval_events": [],
  "started_at": "2026-08-07T00:00:00Z",
  "finished_at": "2026-08-07T00:00:20Z"
}
```

Required fields:

- run_id
- status
- summary
- totals
- results
- verification
- reflection

## Plan Validation Contract

Validate Plan must block execution when any of these fail:

- Dependency graph is invalid (missing or cyclic dependency)
- Permission or policy requirement not satisfied
- Required runtime resource is unavailable
- Steps conflict by write target, lock, or order
- Task requests blocked capability or forbidden target

## Executor Interface Contract

All executors must implement this interface contract:

- name() -> string
- can_handle(task: Task) -> boolean
- execute(task: ScheduledTask, context: RuntimeContext) -> ExecutionResult
- dry_run(task: ScheduledTask, context: RuntimeContext) -> ExecutionResult

Expected executor names for P1 and beyond:

- file
- git
- terminal
- browser
- preview
- railway
- cloudflare
- supabase
- memory
- plugin

## Runtime State Contract

Runtime state is externalized through runtime_state.py.

Minimum state fields:

- run_id
- current_task_id
- current_step
- running_executors
- progress_percent
- eta_seconds
- paused
- cancelled
- completed
- last_update_at

## Approval Contract

- Non-approval tasks continue automatically.
- Approval-required tasks pause at validation or execution boundary.
- Resume requires explicit approval event.
- All approval events are recorded in report.approval_events.

## Non-Goals for P1

- No redesign of ExecutiveKernel.
- No redesign of ExecutiveBrain identity/governance.
- No rebuild of P0.6 capability/permission/execution authorization model.

## Arabic Support / دعم اللغة العربية

- This document supports Arabic interaction and bilingual system design.
- يجب أن يدعم هذا المستند الحوار والمفاهيم باللغة العربية.
- Arabic responses and interfaces should follow founder-approved consent, security, and partner-first behavior.
- يجب أن تبقى المبادئ نفسها ثابتة في التعامل باللغة العربية.
