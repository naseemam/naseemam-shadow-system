# Tool System

## Purpose

The Tool System gives Ameer real execution access to connected capabilities while keeping
execution observable and recoverable. Tool use is operational by default and does not
create a Founder approval gate by itself.

## Connector Principles

- Tools are execution resources controlled by Ameer Core.
- Connected tools may be used directly when Ameer has real access and the operation is inside delegated scope.
- No per-tool Founder approval is required for routine operations.
- Tool connectors may perform technical validation, authentication and scope checks, but they may not invent human approval gates.
- Inputs, outputs and credentials should be handled securely and logged where useful for recovery/audit.

## Tool Categories

- Communication tools (email, messaging)
- Productivity tools (calendar, files, documents, spreadsheets)
- Research tools (web search, databases)
- Project tools (GitHub, issue trackers)
- Infrastructure tools (Railway, Cloudflare, VPS, deployment systems)
- Local execution tools (filesystem, shell, VS Code/local workspace)
- Media tools (images, audio, video)

## Request Lifecycle

1. Receive or infer the required operation from context.
2. Select the appropriate tool automatically.
3. Verify real connector availability and technical scope.
4. Check only the sovereign gate source in `kernel.ameer_authority`.
5. Execute.
6. Verify outcome and retry/repair when needed.
7. Record evidence/result.

## Sovereign Gate Rule

A tool pauses for Founder approval only when the action itself is one of the explicitly
Founder-defined sovereign decisions in `06_Code/kernel/ameer_authority.py`.

Examples that are operational without Founder approval: file creation/editing/deletion,
repository operations inside existing repositories, deployments to existing sites/programs,
DNS configuration, key/token creation/rotation/replacement, worker management, connector
management, research, media creation, spreadsheet/document generation, VPS/local operations.

## Security

- Do not expose secrets unnecessarily in conversation or logs.
- Preserve recoverability and execution evidence.
- A technical failure or missing credential is a technical blocker, not a Founder approval request.
- External provider restrictions remain external constraints; they do not redefine Ameer Core.

## Arabic Support / دعم اللغة العربية

تعمل الأدوات بالعربية والإنجليزية وفق نفس قاعدة التنفيذ المباشر، ولا تظهر موافقة بشرية إلا عند البوابات السيادية المحددة مركزيًا.
