# إطار الامتثال التنفيذي — Executive Compliance Framework

**Project:** Ameer Executive Platform

**Version:** 1.0

**Status:** Active

**Created:** 2026-08-03

**Founder:** Naseem

**Governed by:** `01_Docs/Executive_Constitution_v1.0.md`

---

## الغرض / Purpose

هذه الوثيقة لا تُضيف ميزات جديدة.

بل تُحوّل الدستور التنفيذي إلى قواعد يمكن اختبارها آليًا.

كل Pull Request يجب أن يُجيب على سؤال واحد:

> **هل هذا التغيير ما زال يُحقق Executive Compliance؟**

وليس فقط: هل نجحت الاختبارات؟

---

This document does not add features.

It converts the Executive Constitution into rules that can be automatically tested.

Every Pull Request must answer one question:

> **Does this change still achieve Executive Compliance?**

Not merely: Did the tests pass?

---

## مبدأ الامتثال / Compliance Principle

كل قاعدة في هذا الإطار مستمدة من مبدأ دستوري أو عقد دستوري محدد.
لا يوجد في هذه الوثيقة ما يتعارض مع الدستور — بل هي تُجسّده.

Every rule in this framework is derived from a specific constitutional principle or contract.
Nothing here conflicts with the Constitution — this document embodies it.

---

## جدول الامتثال / Compliance Table

| القاعدة الدستورية | أين تطبَّق | ملف الكود / الطبقة | كيف تُختبر | اختبار Sprint 0 |
|---|---|---|---|---|
| **Executive First** — أمير الواجهة الوحيدة | Executive Core | `06_Code/executive_brain.py` | يُتحقق أن هوية أمير تطابق الدستور في كل رد | `test_identity` |
| **Delegation** — الوكلاء لا يقررون | Reasoning Orchestrator | `06_Code/reasoning_orchestrator.py` | يُتحقق أن الوكلاء لا يصدرون قرارات مستقلة | `test_delegation` |
| **Provider Independence** — المزود بنية تحتية فقط | Provider Adapter | `06_Code/adapters/inference_provider.py` | تبديل OpenAI/Ollama دون تغيير الشخصية أو الهوية | `test_provider_swap` |
| **Memory Governance** — لا كتابة بدون حوكمة | Memory Layer / Executive Brain | `06_Code/executive_brain.py` | رفض الكتابة خارج المسارات المسموحة | `test_memory_governance` |
| **Founder Authority** — رؤية المؤسس المرجع الأعلى | Approval Gate / Guardian | `06_Code/executive_brain.py` | رفض أي قرار جوهري بدون موافقة المؤسس | `test_founder_authority` |
| **Response Integrity** — الهوية متسقة عبر الطبقات | Response Formatter | `06_Code/response_formatter.py` | التحقق أن الرد النهائي يحافظ على هوية أمير | `test_response_integrity` |
| **Constitutional Compliance** — الدستور فوق الكل | All layers | جميع الطبقات | لا مكون يدّعي سلطة تنفيذية بديلة | `test_constitutional_compliance` |

---

## قواعد Sprint 0 المفصّلة / Sprint 0 Detailed Rules

### 1. قاعدة الهوية — Identity Rule

**المبدأ:** Executive First (مبدأ رقم 1) + العقد الأول (Contract 1 — Ameer Identity)

**الشرط:** أمير هو الواجهة التنفيذية الوحيدة. لا مكون آخر يدّعي هذا الدور.

**أين:** `06_Code/executive_brain.py` → `ExecutiveBrain`، `06_Code/agents/identity_agent.py`

**كيف تُختبر:**
- أن الرد على سؤال "من أنت؟" يطابق الهوية المُعرَّفة في `identity.json`
- أن اسم أمير في الرد يطابق `identity["name"]`
- أن المؤسس مُعرَّف بوصفه صاحب القرار النهائي
- أن لا وكيل آخر يُقدّم نفسه كعقل تنفيذي

**ملف الاختبار:** `07_Tests/test_constitutional_compliance.py::IdentityComplianceTests`

---

### 2. قاعدة التفويض — Delegation Rule

**المبدأ:** Delegation, Not Replacement (مبدأ رقم 2) + العقد الثاني (Contract 2 — Agent Contract)

**الشرط:** الوكلاء ينفذون فقط — لا يقررون ولا يصدرون ردودًا نهائية مستقلة.

**أين:** `06_Code/agents/` → جميع الوكلاء، `06_Code/reasoning_orchestrator.py`

**كيف تُختبر:**
- أن كل وكيل يُعيد `reply_draft` لا `final_response`
- أن الرد النهائي يمر عبر `ExecutiveBrain.compose_final_reply`
- أن الوكيل لا يحتفظ بحالة قرار مستقلة بعد تنفيذ المهمة

**ملف الاختبار:** `07_Tests/test_constitutional_compliance.py::DelegationComplianceTests`

---

### 3. قاعدة استقلالية المزود — Provider Independence Rule

**المبدأ:** Provider Independence (مبدأ رقم 3) + العقد الثالث (Contract 3 — Inference Provider Contract)

**الشرط:** تبديل المزود لا يُغيّر هوية أمير أو نبرته أو سلوكه.

**أين:** `06_Code/adapters/inference_provider.py`

**كيف تُختبر:**
- أن `OpenAIProvider` و`OllamaProvider` يُنفّذان نفس الواجهة `InferenceProvider`
- أن تبديل المزود لا يُغيّر هوية أمير (identity لا تأتي من المزود)
- أن كلا المزودين يُعيدان نتيجة أو `None` دون رفع استثناء خارج المتوقع

**ملف الاختبار:** `07_Tests/test_constitutional_compliance.py::ProviderIndependenceTests`

---

### 4. قاعدة حوكمة الذاكرة — Memory Governance Rule

**المبدأ:** Memory Governance (مبدأ رقم 4) + العقد الرابع (Contract 4 — Memory Contract)

**الشرط:** لا كتابة خارج المسارات المُصرَّح بها. أي محاولة كتابة خارج `_ALLOWED_WRITE_PREFIXES` تُرفض.

**أين:** `06_Code/executive_brain.py` → `ExecutionEngine._check_write_allowed`

**كيف تُختبر:**
- أن الكتابة إلى مسار محظور تُعيد `status: blocked`
- أن الكتابة إلى مسار مسموح تُعيد `status: created`
- أن محاولة الكتابة خارج نطاق الـ workspace تُرفض

**ملف الاختبار:** `07_Tests/test_constitutional_compliance.py::MemoryGovernanceTests`

---

### 5. قاعدة سلطة المؤسس — Founder Authority Rule

**المبدأ:** Founder Authority (مبدأ رقم 5) + العقد الخامس (Contract 5 — Founder Contract)

**الشرط:** أي قرار يحتاج موافقة يُوقَف حتى يُؤكّد المؤسس. لا يتجاوز النظام هذا الحاجز تلقائيًا.

**أين:** `06_Code/executive_brain.py` → `ExecutiveBrain.compose_final_reply` + guardian logic

**كيف تُختبر:**
- أن الطلبات ذات `guardian_status == "needs_approval"` لا تُنفَّذ دون تأكيد
- أن الطلبات ذات `guardian_status == "blocked"` تُرفض برسالة واضحة
- أن النظام لا يتجاوز حاجز الموافقة بأي آلية تلقائية

**ملف الاختبار:** `07_Tests/test_constitutional_compliance.py::FounderAuthorityTests`

---

### 6. قاعدة نزاهة الرد — Response Integrity Rule

**المبدأ:** Executive Integrity (قسم النزاهة التنفيذية في الدستور)

**الشرط:** الرد النهائي يحافظ على هوية أمير — لا انجراف هوية، لا تعارض طبقات، لا تلوث من المزود.

**أين:** `06_Code/response_formatter.py`

**كيف تُختبر:**
- أن `ResponseFormatter` يُنتج ردودًا تحتوي على الحقول المطلوبة
- أن الرد لا يُقدّم هوية مخالفة للدستور
- أن تنسيق الرد ثابت بغض النظر عن المزود أو الوكيل

**ملف الاختبار:** `07_Tests/test_constitutional_compliance.py::ResponseIntegrityTests`

---

### 7. قاعدة الامتثال الدستوري الكامل — Constitutional Compliance Rule

**المبدأ:** جميع المبادئ والعقود الدستورية

**الشرط:** لا مكون في النظام يدّعي سلطة تنفيذية، كل وكيل يُعيد `agent` و`reply_draft` (لا قرار نهائي)، الدستور محمي من التغيير الصامت.

**أين:** جميع طبقات النظام

**كيف تُختبر:**
- أن جميع الوكلاء المُسجَّلين يُنفّذون `BaseAgent` ويُعيدون `AgentOutput`
- أن لا وكيل يُعلن عن نفسه كـ executive authority
- أن `ExecutiveBrain` هو النقطة الوحيدة التي تُصدر قرارًا نهائيًا

**ملف الاختبار:** `07_Tests/test_constitutional_compliance.py::ConstitutionalComplianceTests`

---

## بوابة امتثال Pull Request / PR Compliance Gate

قبل دمج أي Pull Request، يجب أن يُجيب على الأسئلة التالية:

| السؤال | المرجع |
|---|---|
| هل الاختبارات نجحت؟ | `07_Tests/` |
| **هل هذا التغيير يُحقق Executive Compliance؟** | هذه الوثيقة |
| هل يُجيب على الأسئلة الأربعة في PR Merge Gate؟ | `Executive_Constitution_v1.0.md` |
| هل نجحت اختبارات Sprint 0؟ | `07_Tests/test_constitutional_compliance.py` |

---

## معايير نجاح Sprint 0 / Sprint 0 Success Criteria

| الاختبار | يُثبت |
|---|---|
| `test_identity` | أمير يعرف من هو — الهوية تطابق الدستور |
| `test_delegation` | الوكلاء لا يقررون — يُفوّضون فقط |
| `test_provider_swap` | الهوية ثابتة بغض النظر عن المزود |
| `test_memory_governance` | الكتابة محكومة — لا كتابة خارج المسارات المسموحة |
| `test_founder_authority` | لا قرار جوهري بدون موافقة المؤسس |
| `test_response_integrity` | الرد النهائي يحافظ على هوية أمير |
| `test_constitutional_compliance` | النظام يُطبّق الدستور — لا مجرد مجموعة ملفات |

إذا نجحت هذه الاختبارات السبعة يمكن القول لأول مرة:

> **أمير أصبح يعمل وفق دستوره.**

---

## العلاقة بالوثائق الأخرى / Relationship to Other Documents

| الوثيقة | الدور |
|---|---|
| `01_Docs/Executive_Constitution_v1.0.md` | المرجع الأعلى — المصدر الذي تُجسّده هذه الوثيقة |
| `07_Tests/test_constitutional_compliance.py` | تنفيذ قواعد هذا الإطار كاختبارات آلية |
| `01_Governance/ADR.md` | قرارات معمارية تعمل تحت هذا الإطار |
| `07_Tests/test_agent_contract.py` | اختبارات عقد الوكلاء (تُكمل قاعدة التفويض) |

---

## Arabic Support / دعم اللغة العربية

- هذه الوثيقة ثنائية اللغة — العربية والإنجليزية متساويتان في السلطة.
- عند أي تعارض في الترجمة يُرجع إلى النص العربي.
