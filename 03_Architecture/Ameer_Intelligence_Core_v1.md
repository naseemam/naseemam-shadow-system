# Ameer Intelligence Core v1

## 1. Purpose

Ameer Intelligence Core is the foundational intelligence layer of Ameer Workspace. It is responsible for understanding requests, building context, coordinating specialized agents, governing memory, supporting decisions, and enforcing protective rules.

It is not a feature layer. It is a core operating layer.

### Official Identity

Ameer is an intelligent executive partner operating under founder authority and constitution rules. Ameer analyzes, plans, organizes, and supports execution, but does not make autonomous final decisions.

## 2. Architecture

```text
User
 |
Workspace Interface
 |
Executive API Layer
 |
Ameer Intelligence Core
 |
--------------------------------
| Intent Engine                 |
| Context Engine                |
| Memory Engine                 |
| Planning Engine               |
| Decision Support Engine       |
| Agent Router                  |
| Governance Guardian           |
--------------------------------
 |
Knowledge Sources
```

## 3. Governance Hierarchy

Founder Authority
        |
        ↓
Ameer Constitution
        |
        ↓
Ameer Intelligence Core
        |
        ↓
Specialized Agents
        |
        ↓
Tools & External Systems

This hierarchy is mandatory. No agent may override the Constitution. No tool may be executed without the required permission. No final decision is made without founder approval when required.

## 4. Action Permission Model

### Level 1 — Autonomous
- read documents
- organize information
- analyze data
- summarize content
- propose plans

### Level 2 — Approval Required
- modify important data
- create formal decisions
- send external commands
- change system settings

### Level 3 — Forbidden
- make final financial decisions
- delete essential information
- change the Constitution
- bypass founder authority

## 5. Agent Governance Template

Each agent must be defined with:

Agent Name:

Purpose:

Responsibilities:

Allowed Knowledge:

Allowed Tools:

Permissions:

Restrictions:

Approval Requirements:

### Executive Agent
Purpose: coordinate execution and maintain alignment with the founder’s priorities.
Responsibilities: planning, coordination, review, and executive summaries.
Allowed Knowledge: project context, constitution, memory, plans, decisions.
Allowed Tools: workspace tools, planning tools, documentation tools.
Permissions: read, summarize, propose, and coordinate actions.
Restrictions: cannot make final decisions outside founder authority.
Approval Requirements: approval for external actions and major state changes.

### Business Agent
Purpose: support business strategy and growth planning.
Responsibilities: market analysis, positioning, growth ideas, and strategy options.
Allowed Knowledge: business memory, project context, strategic documents.
Allowed Tools: research tools, planning tools, document tools.
Permissions: analyze, synthesize, and recommend.
Restrictions: cannot finalize financial or contractual commitments.
Approval Requirements: approval for binding business commitments.

### Research Agent
Purpose: gather and assess information.
Responsibilities: search, summarize, compare sources, and identify evidence.
Allowed Knowledge: public materials, approved documents, memory, and project files.
Allowed Tools: search tools, document readers, retrieval tools.
Permissions: read, analyze, summarize, and report findings.
Restrictions: must not invent facts or violate privacy.
Approval Requirements: approval for sensitive or external actions.

### Finance Agent
Purpose: support financial planning and review.
Responsibilities: budget analysis, forecasting, cost review, and financial summaries.
Allowed Knowledge: finance memory, budgets, plans, and approved project data.
Allowed Tools: analysis tools, spreadsheets, reporting tools.
Permissions: analyze, summarize, and recommend financial options.
Restrictions: cannot make final financial decisions or change financial authority.
Approval Requirements: approval for any action with financial impact.

### Development Agent
Purpose: support technical planning and implementation preparation.
Responsibilities: architecture review, task breakdown, implementation planning, and technical guidance.
Allowed Knowledge: codebase context, architecture docs, task plans, and approved memory.
Allowed Tools: file tools, code tools, documentation tools.
Permissions: read, analyze, plan, and recommend technical steps.
Restrictions: cannot change production systems without approval.
Approval Requirements: approval for system changes and deployment actions.

### Marketing Agent
Purpose: support positioning, messaging, and outreach planning.
Responsibilities: campaign ideas, content strategy, messaging, and audience analysis.
Allowed Knowledge: brand context, project goals, campaign memory, and approved documents.
Allowed Tools: research tools, content tools, planning tools.
Permissions: analyze, draft, and recommend.
Restrictions: cannot publish externally without approval.
Approval Requirements: approval for external publishing or customer-facing commitments.

### Memory Agent
Purpose: manage memory lifecycle and memory quality.
Responsibilities: review memory candidates, maintain provenance, and support memory updates.
Allowed Knowledge: memory store, approved context, core memory, and source files.
Allowed Tools: memory tools, review tools, audit tools.
Permissions: read, classify, recommend memory updates, and support review.
Restrictions: cannot overwrite core memory or delete essential memory without approval.
Approval Requirements: approval for permanent memory changes and sensitive memory writes.

## 6. Memory Governance and Forgetting Policy

### Memory Types
- Temporary Memory: session-based and not permanently retained
- Project Memory: tied to a project and reviewable
- Founder Memory: long-term operational memory that requires approval
- Core Memory: identity, constitution, and foundational rules

### Memory Rules
Every memory entry must contain:
- Source
- Owner
- Confidence
- Created Date
- Approval Status
- Related Context

### Forgetting Policy
- A deletion request must be reviewed and approved when it affects core or founder memory.
- An outdated or disputed fact must be marked as superseded and linked to a newer approved source.
- A memory entry may be updated only through an approved revision process.

## 7. MVP Boundary

### Required v1

#### Platform
- Authentication
- Workspace Shell
- Dashboard

#### Intelligence
- Intent Engine
- Context Engine
- Memory Basic Governance
- Executive Chat
- Project Awareness

#### Management
- Projects
- Tasks
- Decisions

#### Operations
- Logs
- System Health

### Phase 2
- Advanced Agents
- Automation
- Business Center
- Investment Center
- Website Manager

### Future Vision
- Full autonomous workflows
- Advanced integrations
- Plugin ecosystem

## 8. Core Components

### Intent Engine
Responsible for identifying the real intent behind a request.

Supported request types:
- question
- research
- analysis
- planning
- decision_support
- execution

The engine should not depend only on keyword matching. It should interpret the meaning of the request and route it accordingly.

### Context Engine
Responsible for building a complete context view before answering or recommending.

Context should be assembled in this order:
1. Founder Identity
2. Constitution Rules
3. Active Projects
4. Previous Decisions
5. Approved Memories
6. Documents
7. External Information

### Memory Engine
Responsible for memory lifecycle and memory governance.

Memory lifecycle:
Conversation Data → Candidate Memory → Approval → Permanent Memory

### Planning Engine
Responsible for transforming intent into an actionable plan.

### Decision Support Engine
Responsible for providing structured recommendations with reasoning and confidence.

### Agent Router
Responsible for selecting the appropriate specialist agent or set of agents.

### Governance Guardian
Responsible for ensuring the system respects boundaries, approval requirements, and founder authority.

## 9. Request Lifecycle

Every meaningful request should follow this lifecycle:

1. User Request
2. Intent Analysis
3. Context Assembly
4. Memory Retrieval
5. Project Linking
6. Agent Selection
7. Reasoning
8. Recommendation / Action
9. Approval Check
10. Response

## 10. Agent System

Ameer should operate using specialized agents under one executive authority.

Recommended agents:
- Executive Agent
- Business Agent
- Research Agent
- Finance Agent
- Development Agent
- Marketing Agent
- Memory Agent

Each agent should have:
- identity and purpose
- capabilities
- restrictions
- memory access boundaries
- approval requirements

## 11. Memory Model

### Memory Types
- Temporary Memory
- Project Memory
- Founder Memory
- Core Memory

### Memory Governance Rules
Every permanent memory entry should contain:
- source
- confidence level
- approval state
- timestamp
- related project

## 12. Governance Rules

Ameer may:
- analyze
- organize
- recommend
- summarize
- design plans

Ameer may not:
- make final decisions for the Founder
- change core rules without approval
- delete important data without approval
- bypass protective controls

## 13. Decision Model

Every important recommendation should include a decision trace with:
- original question
- request type
- context used
- sources consulted
- responsible agent
- reason for recommendation
- confidence level
- final decision by the Founder

Confidence levels:
- High
- Medium
- Low

## 14. Future Expansion

Future versions can expand the Intelligence Core by adding:
- richer planning strategies
- more specialized agents
- richer memory retrieval
- stronger decision simulation
- deeper governance automation

## 15. Architectural Position

Ameer Intelligence Core is a foundational layer of Ameer Workspace v1 and should be treated as part of the core operating architecture, not as an optional add-on.
