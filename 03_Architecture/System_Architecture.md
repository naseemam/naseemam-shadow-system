# System Architecture

## Purpose

This document provides a single high-level architecture map for Ameer so that developers and agents can quickly understand how the main system documents, runtime components, and product layers connect.

## Architecture Hierarchy

```text
Founder
  |
  v
Executive Core (Ameer)
  |
  +--> Executive Brain
  |      |
  |      v
  |   Reasoning Orchestrator
  |      |
  |      +--> Memory
  |      +--> Knowledge
  |      +--> Specialized Agents
  |      +--> Providers (OpenAI / Ollama / future adapters)
  |
  +--> Backend
  |      |
  |      +--> Runtime
  |      +--> API Layer
  |      +--> Document Loading
  |      +--> Governance / Response Formatting
  |
  +--> Frontend
         |
         +--> Workspace Shell
         +--> Dashboard / Modules
         +--> Executive Chat
```

## Core Relationship Summary

### 1. Executive Core (Ameer)

Executive Core is the top operating identity of the system.
It is the founder-facing executive partner and the single authority that coordinates all internal intelligence behavior.

It is defined and constrained by:
- `01_Docs/Ameer_Constitution_v0.1.md`
- `03_Architecture/Ameer_Operating_Model.md`
- `03_Architecture/Ameer_Architecture_Overview.md`
- `03_Architecture/Ameer_Intelligence_Core_v1.md`

Executive Core sits above all specialized agents and remains the only direct executive layer representing Ameer to the founder.

### 2. Executive Brain

Executive Brain is the thinking policy layer that decides how Ameer should interpret a request, when to respond directly, when to plan, and when to route work to another agent.

Primary reference:
- `03_Architecture/Executive_Brain.md`

Executive Brain depends on:
- Executive Core authority and rules
- Reasoning Orchestrator for routing and source selection
- Governance checks before impactful actions

### 3. Reasoning Orchestrator

Reasoning Orchestrator is the execution-facing reasoning layer that applies routing policy, selects sources, tracks intent, and maps a request to the right internal executor.

References:
- `03_Architecture/Ameer_Mind_Orchestrator.md`
- `/home/runner/work/naseemam-shadow-system/naseemam-shadow-system/06_Code/reasoning_orchestrator.py`

Its role is to connect Executive Brain with actual retrieval and agent execution.
It reads documents, applies source-priority rules, identifies the route, and decides whether work stays in Ameer Core or moves to a specialized agent.

### 4. Memory

Memory is the approved long-term and session-aware recall layer.
It stores and governs founder memory, project memory, decision history, and temporary context.

Primary references:
- `03_Architecture/Memory_System.md`
- `04_Memory/*`

Memory is used by the Reasoning Orchestrator and specialized agents to ground answers in approved context.
Memory does not override the Constitution or Executive Core rules.

### 5. Knowledge

Knowledge is the document and reference layer used to provide broader context beyond stored memory.
It includes architecture files, plans, documentation, and approved project materials loaded into the system.

Primary sources include:
- `01_Docs/*`
- `03_Architecture/*`
- selected repository documentation loaded by the backend

Knowledge differs from Memory:
- Memory contains approved retained facts and preferences
- Knowledge contains reference material, system design, and project documentation

### 6. Providers (OpenAI / Ollama)

Providers are the model and inference backends used to generate or support responses.
They are replaceable infrastructure components rather than the identity of Ameer itself.

References:
- `03_Architecture/Ameer_Architecture_Overview.md`
- `/home/runner/work/naseemam-shadow-system/naseemam-shadow-system/06_Code/adapters/inference_provider.py`

Providers sit below the intelligence layers and are accessed through adapters so that model choice can change without changing Ameer identity, governance, or memory rules.

### 7. Specialized Agents

Specialized Agents are subordinate execution and analysis units used when the request requires focused handling.
They operate under Executive Core supervision, not as independent founder-facing systems.

References:
- `03_Architecture/Ameer_Intelligence_Core_v1.md`
- `/home/runner/work/naseemam-shadow-system/naseemam-shadow-system/06_Code/agents/registry.py`
- `/home/runner/work/naseemam-shadow-system/naseemam-shadow-system/06_Code/agents/*`

Typical examples include:
- Identity handling
- Memory management
- Project support
- Research support
- Recovery handling

The user interacts with Ameer, and Ameer decides whether one of these agents should be used internally.

### 8. Frontend

Frontend is the workspace interface layer through which the founder interacts with the system.
It provides shell navigation, modules, views, and the executive chat surface.

References:
- `03_Architecture/Ameer_Workspace_v1_Product_Spec.md`
- `/home/runner/work/naseemam-shadow-system/naseemam-shadow-system/09_Assets/web/index.html`
- `/home/runner/work/naseemam-shadow-system/naseemam-shadow-system/09_Assets/web/modules/*`

Frontend depends on Backend APIs and runtime availability.
It does not own reasoning logic; it presents and organizes the experience.

### 9. Backend

Backend is the application layer that loads system documents, exposes APIs, invokes reasoning and executive components, and returns structured responses to the frontend.

Primary implementation:
- `/home/runner/work/naseemam-shadow-system/naseemam-shadow-system/ameer_server.py`

Backend responsibilities include:
- loading the document corpus
- hosting the API layer
- invoking Executive Brain and Reasoning Orchestrator
- managing runtime metadata
- serving frontend assets
- enforcing response and system boundaries

### 10. Runtime

Runtime is the operating environment that starts and hosts the system.
It defines the entrypoint, server process, host, port, and stable execution rules.

References:
- `03_Architecture/Runtime_Architecture.md`
- `/home/runner/work/naseemam-shadow-system/naseemam-shadow-system/ameer_runtime.py`
- `/home/runner/work/naseemam-shadow-system/naseemam-shadow-system/start_ameer.py`

Runtime sits underneath Backend and Frontend and ensures the whole workspace runs as one governed application.

## End-to-End System Flow

```text
Founder Request
  -> Frontend
  -> Backend API
  -> Executive Core
  -> Executive Brain
  -> Reasoning Orchestrator
  -> Memory + Knowledge + Specialized Agents + Providers
  -> Response Assembly
  -> Backend
  -> Frontend
  -> Founder
```

## Document-to-Component Mapping

| Layer / Component | Main Role | Primary Documents | Primary Implementation |
|---|---|---|---|
| Executive Core (Ameer) | Founder-facing executive authority | `Ameer_Architecture_Overview.md`, `Ameer_Intelligence_Core_v1.md`, `Ameer_Operating_Model.md` | System-wide behavior across backend and orchestration |
| Executive Brain | Thinking and decision policy | `Executive_Brain.md` | `06_Code/executive_brain.py` |
| Reasoning Orchestrator | Intent routing and source policy | `Ameer_Mind_Orchestrator.md` | `06_Code/reasoning_orchestrator.py` |
| Memory | Long-term approved recall | `Memory_System.md`, `04_Memory/*` | Memory files and related agents |
| Knowledge | Documents and reference context | `01_Docs/*`, `03_Architecture/*` | Document loader in `ameer_server.py` |
| Providers | Model inference backends | `Ameer_Architecture_Overview.md` | `06_Code/adapters/*` |
| Specialized Agents | Focused internal execution | `Ameer_Intelligence_Core_v1.md` | `06_Code/agents/*` |
| Frontend | Workspace experience | `Ameer_Workspace_v1_Product_Spec.md` | `09_Assets/web/*` |
| Backend | API and orchestration host | `Runtime_Architecture.md` and related architecture docs | `ameer_server.py` |
| Runtime | Process, host, port, startup rules | `Runtime_Architecture.md` | `ameer_runtime.py`, `start_ameer.py` |

## Architectural Rules

- Executive Core is the single founder-facing authority.
- Executive Brain defines how requests are interpreted and escalated.
- Reasoning Orchestrator applies source and routing policy before broad retrieval.
- Memory and Knowledge support reasoning but do not override governance.
- Specialized Agents are internal workers under Ameer supervision.
- Providers are replaceable infrastructure, not identity.
- Frontend and Backend are delivery layers around the intelligence core.
- Runtime preserves the single-server operating model of the workspace.

## Relationship to Existing Documents

This document acts as the top-level map that connects the more detailed architecture documents.
It should be read first before drilling down into:
- `Executive_Brain.md`
- `Ameer_Intelligence_Core_v1.md`
- `Ameer_Mind_Orchestrator.md`
- `Memory_System.md`
- `Runtime_Architecture.md`
- `Ameer_Workspace_v1_Product_Spec.md`

## Arabic Support / دعم اللغة العربية

- This document supports Arabic interaction and bilingual system design.
- يجب أن تساعد هذه الوثيقة أي مطور أو وكيل على فهم البنية الكاملة للنظام بسرعة.
- Arabic responses, interfaces, and workflows must preserve the same founder authority, approval, and governance architecture.
- يجب أن تبقى العلاقة بين الواجهة، الخلفية، طبقات التفكير، الذاكرة، والوكلاء واضحة ومتسقة في جميع الوثائق.
