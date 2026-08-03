# Architecture Baseline

## Baseline version
- Version marker: v0.3-architecture-freeze
- Snapshot date: 2026-08-02
- Status: stable reference baseline for future LLM and planning work

## Purpose
This document freezes the current architecture posture of the Ameer workspace so subsequent changes can be compared against a known-good structure.

## Current architecture summary

### 1. Runtime layer
- Primary runtime entrypoint: [ameer_server.py](ameer_server.py)
- Startup launcher: [start_ameer.py](start_ameer.py)
- Runtime behavior is centered on a local FastAPI-style request flow and document retrieval.

### 2. Reasoning and executive layer
- Orchestration logic: [06_Code/reasoning_orchestrator.py](06_Code/reasoning_orchestrator.py)
- Executive planning logic: [06_Code/executive_brain.py](06_Code/executive_brain.py)
- These modules coordinate intent classification, routing, context assembly, and response shaping.

### 3. Agent layer
- Specialized agents live under [06_Code/agents](06_Code/agents)
- The current implementation is modular and uses a registry-driven agent model.

### 4. Knowledge and memory layer
- Core documents and governance materials live in [01_Docs](01_Docs)
- Long-term memory notes live in [04_Memory](04_Memory)
- Architecture references live in [03_Architecture](03_Architecture)

### 5. Development hygiene layer
- Temporary diagnostics and manual tests should be stored under [08_DevTools](08_DevTools)
- Production runtime files remain in the main runtime surface and should not be repurposed for ad hoc checks.

## Baseline boundaries
- This snapshot intentionally avoids behavioral changes to the runtime surface.
- Core routing, executive reasoning, and agent contracts remain the reference state.
- Future work should be introduced as incremental changes on top of this baseline.

## Reference files
- [03_Architecture/Ameer_Architecture_Overview.md](03_Architecture/Ameer_Architecture_Overview.md)
- [03_Architecture/Ameer_Intelligence_Core_v1.md](03_Architecture/Ameer_Intelligence_Core_v1.md)
- [03_Architecture/Ameer_Mind_Orchestrator.md](03_Architecture/Ameer_Mind_Orchestrator.md)
- [README.md](README.md)

## Notes for future work
- Add new LLM or inference adapters as isolated enhancements.
- Preserve the existing orchestration contract unless a breaking change is explicitly approved.
- Keep new temporary scripts inside [08_DevTools](08_DevTools) rather than the workspace root.
