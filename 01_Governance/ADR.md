# Architecture Decision Record (ADR)

## Purpose

This document is the official record for major architectural decisions in Ameer.
Its purpose is to ensure that critical system decisions are documented in a stable, reviewable place instead of remaining scattered across conversations, memory, or implicit implementation choices.

It should be updated whenever a high-impact architectural decision is adopted, changed, or superseded.

## How to Use This Document

- Record major architectural decisions that shape system structure, responsibility boundaries, governance, runtime, or core operating behavior.
- For each decision, capture the context, the chosen direction, and the reason.
- When a decision changes later, add a new record rather than silently rewriting history.
- Architecture documents describe the system design; this ADR explains why certain key choices were made.

## Constitutional Constraint / القيد الدستوري

**ADR cannot override the Executive Constitution.**

No architectural decision recorded here may contradict, bypass, or supersede any principle, contract, or rule defined in `01_Docs/Executive_Constitution_v1.0.md`. If a proposed architectural decision conflicts with the Constitution, the Constitution takes precedence. The decision must be revised, or a formal Founder-approved governance change must be initiated first.

لا يجوز لأي قرار معماري مسجل هنا أن يتعارض مع الدستور التنفيذي أو يتجاوزه أو يحل محله. إذا تعارض أي قرار معماري مقترح مع الدستور، فالدستور هو المرجع. يجب مراجعة القرار، أو البدء بتغيير رسمي في الحوكمة يعتمده المؤسس أولاً.

## Decision Record Format

Each decision should include:
- ID
- Title
- Status
- Date
- Decision
- Rationale
- Consequences
- Related Documents

---

## ADR-001 — Ameer is the Executive Core

- **Status:** Accepted
- **Date:** 2026-08-03

### Decision
Ameer is defined as the Executive Core of the system and serves as the single founder-facing executive authority.

### Rationale
The system is designed around one coherent operating identity rather than multiple peer agents speaking independently. This preserves a stable relationship with the founder, keeps accountability centralized, and ensures all important actions remain governed by one constitutional authority.

### Consequences
- Ameer becomes the top operational identity in the architecture.
- All internal intelligence layers and specialized agents operate under Ameer supervision.
- Governance, approval, and response quality are easier to enforce consistently.

### Related Documents
- `01_Docs/Ameer_Constitution_v0.1.md`
- `03_Architecture/Ameer_Architecture_Overview.md`
- `03_Architecture/Ameer_Intelligence_Core_v1.md`
- `03_Architecture/System_Architecture.md`

---

## ADR-002 — Specialized Agents do not talk directly to the user

- **Status:** Accepted
- **Date:** 2026-08-03

### Decision
Specialized agents operate as internal workers and do not directly represent themselves to the founder in normal system flow.

### Rationale
This keeps the interaction model simple and predictable. The founder speaks to one executive partner, while internal agents remain subordinate execution units. This avoids conflicting voices, inconsistent policy application, and fragmented responsibility.

### Consequences
- Ameer remains the only primary conversational interface.
- Specialized agents focus on analysis, retrieval, and execution support.
- Final synthesis, tone, and approval framing stay centralized.

### Related Documents
- `03_Architecture/Executive_Brain.md`
- `03_Architecture/Ameer_Intelligence_Core_v1.md`
- `03_Architecture/System_Architecture.md`

---

## ADR-003 — Response composition is a dedicated architectural responsibility

- **Status:** Accepted
- **Date:** 2026-08-03

### Decision
The system maintains a distinct response composition responsibility so that retrieved context, agent outputs, governance checks, and final founder-facing language are assembled in a controlled layer.

### Rationale
Reasoning, retrieval, routing, and final communication are not the same concern. Separating final response composition improves consistency, allows better governance framing, and prevents raw internal outputs from being exposed directly to the founder.

### Consequences
- Internal outputs can be normalized before delivery.
- Approval language, executive framing, and bilingual clarity can be enforced consistently.
- Future response formatting improvements can be made without redesigning other reasoning layers.

### Related Documents
- `03_Architecture/Decision_Engine.md`
- `03_Architecture/Executive_Brain.md`
- `03_Architecture/System_Architecture.md`
- `/home/runner/work/naseemam-shadow-system/naseemam-shadow-system/06_Code/response_formatter.py`

---

## ADR-004 — Provider layer remains separate from Ameer identity

- **Status:** Accepted
- **Date:** 2026-08-03

### Decision
Model providers such as OpenAI, Ollama, or future inference backends are treated as replaceable provider infrastructure rather than as the core identity or logic of Ameer.

### Rationale
Ameer must preserve identity, memory, governance, and operating behavior even if the underlying model changes. Keeping providers behind a dedicated layer makes the system modular and prevents provider choice from becoming the definition of the product itself.

### Consequences
- The system can switch or combine providers with lower architectural risk.
- Ameer identity and governance stay stable across model changes.
- Provider-specific logic stays isolated from higher reasoning layers.

### Related Documents
- `03_Architecture/Ameer_Architecture_Overview.md`
- `03_Architecture/Ameer_Operating_Model.md`
- `03_Architecture/System_Architecture.md`
- `/home/runner/work/naseemam-shadow-system/naseemam-shadow-system/06_Code/adapters/inference_provider.py`

---

## ADR-005 — OpenAI is a provider, not the core architecture

- **Status:** Accepted
- **Date:** 2026-08-03

### Decision
When OpenAI is used, it is used as one inference provider within the provider layer, not as the architectural core of the system.

### Rationale
The system must remain portable, modular, and resilient to provider changes. Treating OpenAI as a provider avoids coupling the full architecture to one external model vendor and preserves the ability to use local or alternative backends later.

### Consequences
- OpenAI integration can be replaced, supplemented, or deprioritized later.
- The project can keep a local-first or hybrid direction.
- Governance and memory rules remain independent from vendor capabilities.

### Related Documents
- `03_Architecture/Ameer_Architecture_Overview.md`
- `03_Architecture/System_Architecture.md`

---

## ADR-006 — Memory is an independent architectural layer

- **Status:** Accepted
- **Date:** 2026-08-03

### Decision
Memory is treated as a distinct architectural layer, separate from general knowledge, reasoning flow, and provider infrastructure.

### Rationale
Long-term retained founder context requires stronger governance, provenance, approval control, and update discipline than general documents or model context windows. Separating memory helps preserve trust and prevents persistent knowledge from being mixed casually with temporary inference state.

### Consequences
- Memory can follow explicit approval and lifecycle rules.
- Retrieval can distinguish between approved memory and general knowledge documents.
- The architecture can evolve memory governance without restructuring all reasoning logic.

### Related Documents
- `03_Architecture/Memory_System.md`
- `03_Architecture/Ameer_Intelligence_Core_v1.md`
- `03_Architecture/System_Architecture.md`
- `04_Memory/*`

---

## ADR-007 — Runtime is a single governed runtime

- **Status:** Accepted
- **Date:** 2026-08-03

### Decision
Ameer runs as a single governed runtime with one main startup path, one primary server, and one stable operating environment.

### Rationale
A single runtime simplifies operations, reduces fragmentation, preserves architectural discipline, and keeps frontend, backend, and intelligence layers under one controlled execution model. This also supports the project's explicit runtime freeze and change governance.

### Consequences
- Startup, routing, hosting, and asset serving remain centralized.
- Architectural drift from multiple competing local runtimes is reduced.
- Runtime changes become explicit governance decisions rather than ad hoc engineering changes.

### Related Documents
- `03_Architecture/Runtime_Architecture.md`
- `03_Architecture/System_Architecture.md`
- `/home/runner/work/naseemam-shadow-system/naseemam-shadow-system/ameer_runtime.py`
- `/home/runner/work/naseemam-shadow-system/naseemam-shadow-system/ameer_server.py`
- `/home/runner/work/naseemam-shadow-system/naseemam-shadow-system/start_ameer.py`

---

## ADR-008 — Executive Capability Governance (P0.6)

- **Status:** Accepted
- **Date:** 2026-08-06

### Decision

Introduce a three-layer Capability Governance system consisting of:
1. **CapabilityRegistry** — tracks capability lifecycle (core/extended/experimental/suspended/deprecated/retired) with conflict detection
2. **PermissionRegistry** — separates capability ownership from execution permission (owned / enabled / permission_status)
3. **ExecutionAuthorization** — provides per-action runtime authorization (approved / denied / pending)

Core capabilities (engineering, programming, system_design, project_management, analysis, planning) are seeded at boot and sealed permanently. All other capability expansion requires Founder approval, conflict-check pass, and simulation before activation.

### Rationale

Ameer must be able to grow its executive toolkit over time without risking identity drift or unauthorized execution. Separating "what Ameer knows" from "what Ameer is allowed to do" enables:
- Permanent capability knowledge (capabilities are never deleted, only lifecycle-transitioned)
- Controlled, per-action execution gating
- Full audit trail for every permission grant, revocation, and execution

This also enforces the Founder Authority Contract at the implementation level: no capability can be activated, no permission can be granted, and no execution can be authorized without going through the governed pipeline.

### Consequences

- Three new kernel components boot with ExecutiveKernel.
- `.ameer/` gains three new JSON stores: `capabilities.json`, `permissions.json`, `execution_auth.json`.
- `before_request` context now includes `capability_governance` snapshot and `pending_execution_requests`.
- `health()` now reports `active_capabilities` and `pending_execution_requests`.
- 39 new acceptance tests cover all three components and their kernel integration.

### Related Documents

- `01_Docs/Executive_Constitution_v1.0.md`
- `03_Architecture/Executive_Capability_Governance.md`
- `06_Code/kernel/capability_registry.py`
- `06_Code/kernel/permission_registry.py`
- `06_Code/kernel/execution_authorization.py`
- `07_Tests/test_p06_capability_governance.py`

---

## Relationship to Other Documents

- `01_Docs/Executive_Constitution_v1.0.md` is the supreme governing document above this ADR. Constitutional Contracts defined there are non-negotiable and take precedence over any architectural decision.
- `03_Architecture/System_Architecture.md` explains how the major components connect.
- Architecture documents in `03_Architecture/` explain structure and behavior.
- This ADR explains why the most important structural choices were made.
- Governance changes that affect architecture should be reflected here.

## Arabic Support / دعم اللغة العربية

- This document supports Arabic interaction and bilingual system design.
- يجب أن توثق هذه الوثيقة القرارات المعمارية المهمة بشكل رسمي بدل بقائها ضمن المحادثات فقط.
- Arabic governance and architecture decisions must preserve the same founder authority and approval model.
- يجب أن تكون أسباب القرارات المعمارية الأساسية واضحة لأي مطور أو وكيل يعمل على المشروع.
