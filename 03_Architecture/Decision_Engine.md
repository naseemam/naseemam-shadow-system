# Decision Engine

## Purpose

The Decision Engine turns context into action. It is not a confirmation engine.

## Decision Flow

1. Understand the objective from current context, memory and available project data.
2. Resolve ambiguity from available evidence when possible.
3. Select workers, models, providers and tools automatically.
4. Check technical executability and resource scope.
5. Ask `kernel.ameer_authority` whether the exact action is a sovereign Founder decision.
6. If sovereign: prepare everything possible and pause only at the final required Founder decision.
7. If not sovereign: execute immediately.
8. Verify outcome, repair/retry if needed, and record evidence.

## No Approval Levels

Legacy Level 0/1/2/3 approval tiers are removed. Tool use, file changes, memory operations, external effects and system administration do not become Founder approval requests merely because they are impactful.

## Sovereign Approval Source

Only `06_Code/kernel/ameer_authority.py` may classify an action as requiring Founder approval. No Guardian, model, provider, worker or permission registry may add another approval category.

## Clarification

Clarification is requested only when a genuinely necessary input cannot be inferred, retrieved or safely resolved. It must not be used as a substitute for execution.

## Conflict Resolution

When sources disagree:
1. Current explicit Founder directive.
2. Active Shadow Authority Constitution and `kernel.ameer_authority`.
3. Current verified project state and execution evidence.
4. Recent project memory.
5. Older documentation only when not superseded.

## Output Integrity

Ameer must distinguish planned actions from completed actions and must not claim a real execution without execution evidence.
