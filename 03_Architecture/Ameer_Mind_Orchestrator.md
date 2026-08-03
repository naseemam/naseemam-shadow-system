# Ameer Mind Orchestrator

## Purpose

This document defines how Ameer decides what to read before answering.

The Mind is not a memory store. The Mind is a decision layer that routes the question to the right sources in the right order.

## Core Rule

Ameer must apply source-priority routing before similarity-based retrieval.

If multiple files are needed, Ameer reads by priority order, not by similarity order.

## Mandatory Routing Policies

1. Identity questions:
- Read: `01_Docs/Ameer_Constitution_v0.1.md`
- Scope: Constitution-first and Constitution-anchored response.

2. Memory questions:
- Read: `04_Memory/*`
- Scope: Memory files as primary source.

3. Project questions:
- Read in order:
- `01_Docs/Master_Plan.md`
- Project context files (for example `04_Memory/Projects.md`, then project-specific documents)

4. Investment questions:
- Read in order:
- `04_Memory/Finance.md`
- `04_Memory/Investment.md` (if present), then other finance-related memory files.

5. Execution questions:
- Read in order:
- `03_Architecture/*`
- `06_Code/*`

## Response Contract

Every answer should include internally:
- Intent classification
- Source policy route
- Priority order used
- Retrieved evidence
- Final response synthesis

## Non-Negotiables

- The Constitution always overrides any conflicting source.
- Founder authority is final.
- No action may proceed without the required approval level.
- When evidence is insufficient, ask for clarification.
- Do not silently switch to broad search before applying policy routing.

## Arabic Support / دعم اللغة العربية

- هذه الوثيقة تعرف طبقة العقل في أمير كطبقة قرار، وليست طبقة ذاكرة.
- يجب تطبيق قاعدة توجيه المصادر بالأولوية قبل أي تشابه نصي.
- إذا احتاج أمير أكثر من ملف، يجب القراءة بترتيب الأولوية المحدد في هذه الوثيقة.
- تبقى وثيقة الدستور المرجع الأعلى عند التعارض.
