# Security

## Purpose

Security protects Ameers data, tools, and trust relationship with the Founder.
It also defines the boundaries for safe interaction and external access.

## Security Principles

- Founder control is mandatory for sensitive operations.
- Data should be encrypted at rest and in transit.
- Audit trails must record all impactful actions.
- Least privilege should apply to all tool connectors and memory access.
- Governance and risk management should guide decisions, tool use, and system changes.

## Governance and Risk Management

- Define governance structures for approval, review, and escalation.
- Identify risk categories for data, tools, decisions, operations, and website systems.
- Maintain a risk register and mitigation plan for high-impact workflows.
- Use consistent review cycles to validate compliance and authority.

## Data Protection

- Store approved memory using encryption.
- Protect sensitive memory with additional access controls.
- Mask or redact secrets before storing or sharing.
- Retain only what is necessary for the task.
- Treat founder-owned websites as privacy-critical systems.
- Design, detect, and block no-tracking systems on founder websites.
- Audit third-party trackers, scripts, cookies, and network calls that may compromise privacy.
- Prevent unauthorized tracking and preserve website visitor privacy.
- Use privacy-first analytics only with explicit Founder approval.

## Website Privacy Compliance

- Define a privacy and tracking compliance program for all founder-owned websites.
- Scan sites regularly for embedded trackers, fingerprinting scripts, analytics tags, and cross-site data leaks.
- Enforce a blocklist of unauthorized tracking domains and script loaders.
- Maintain an audit log for website privacy checks, changes, and approvals.
- Use explicit Founder consent before enabling any new analytics, marketing, or tracking integrations.
- Report website privacy posture and tracking risk to the Founder on a regular basis.
- Update privacy controls whenever site features or third-party integrations change.

## Access Control

- Use explicit permissions for tool usage.
- Separate read-only access from write or execute access.
- Require approval for external communications and data export.
- Support permission revocation at any time.

## Audit & Accountability

- Log requests, approvals, and actions.
- Capture who authorized each impactful decision.
- Make logs available to the Founder on demand.
- Include timestamps, request context, and outcome.

## Risks and Mitigations

- Risk: accidental data sharing.
  - Mitigation: always confirm before external output.
- Risk: unauthorized memory updates.
  - Mitigation: require Founder approval for long-term storage.
- Risk: tool connector abuse.
  - Mitigation: sandbox tools and enforce strict policies.

## Arabic Support / دعم اللغة العربية
- Security guidance should explicitly cover Arabic language interactions and consent prompts.
- يجب أن تشمل الضوابط الأمنية التواصل والموافقات باللغة العربية دون تخفيف للسلامة.
- Arabic communications must use the same redaction and privacy protections as English communications.

