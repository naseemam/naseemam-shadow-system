# Release Notes — v1.0.0-P0.4-Executive-Activation

**الإصدار:** `v1.0.0-P0.4-Executive-Activation`  
**التاريخ:** 2026-08-05  
**الحالة:** منتهي ✅  
**الفرع:** `copilot/p0-4-executive-agent-activation`

---

## ما يمثله هذا الإصدار

P0.4 يُفعّل العقل التنفيذي لأمير بثلاثة مكونات جوهرية:

1. **محرك القرارات (DecisionEngine)** — كل قرار مهم يُسجَّل مع السبب والنتيجة.
2. **بوابة الموافقة (ApprovalGate)** — الإجراءات الحساسة لا تُنفَّذ دون موافقة المؤسسة.
3. **الإحاطة الاستباقية (Proactive Briefing)** — أمير يُحاط بالوضع تلقائياً عند أول رسالة.

---

## ما تم إنجازه في P0.4

### DecisionEngine — `06_Code/kernel/decision_engine.py`
- تسجيل القرارات مع: العنوان، السبب، الفئة، النتيجة المتوقعة
- تحديث النتيجة الفعلية وتغيير الحالة (pending → completed/rejected)
- استرجاع القرارات: pending، recent، get by ID
- ديمومة عبر الجلسات في `.ameer/decisions.json`
- حد أقصى 50 قراراً (تُحذف الأقدم تلقائياً)

### ApprovalGate — `06_Code/kernel/approval_gate.py`
- طلب موافقة لأنواع الإجراءات: delete, publish, external, financial, config, other
- الإجراءات عالية الخطورة (delete, publish, external, financial) تُصنَّف تلقائياً بـ `requires_approval=True`
- تسجيل الموافقة أو الرفض مع السبب والجهة
- ديمومة عبر الجلسات في `.ameer/approvals.json`
- حد أقصى 100 طلب

### ExecutiveKernel — `06_Code/kernel/executive_kernel.py`
- boot() يُهيّئ DecisionEngine و ApprovalGate كمكونات رسمية
- before_request() يُعيد `pending_approval_requests` و `proactive_briefing`
- الإحاطة الاستباقية تظهر في أول رسالة فقط، وتشمل: المشاريع، الموافقات المعلّقة، القرارات المعلّقة، المهام الجارية
- health() يُعيد `pending_decisions` و `pending_approval_requests`
- helper methods: `record_decision()`, `request_approval()`

### ameer_server.py
- `GET /decisions` — ملخص القرارات الأخيرة
- `POST /decisions` — تسجيل قرار جديد
- `GET /approvals` — ملخص طلبات الموافقة
- `POST /approvals` — إنشاء طلب موافقة جديد
- `POST /approvals/{id}/approve` — موافقة المؤسسة
- `POST /approvals/{id}/reject` — رفض المؤسسة
- `utf8_json_response` يقبل الآن `status_code` اختياري

### الاختبارات
- **53 اختبار جديد** في `07_Tests/test_p04_executive_activation.py`
- إجمالي الاختبارات: **169 اختبار ناجح**
- يغطي: DecisionEngine، ApprovalGate، ExecutiveKernel، ameer_server endpoints

---

## معيار الإنهاء (Gate P0.4)

- [x] DecisionEngine يحفظ القرارات ويستعيدها عبر الجلسات
- [x] ApprovalGate يحجب الإجراءات الحساسة حتى الموافقة
- [x] الكيرنل يُنتج إحاطة استباقية في أول رسالة
- [x] الـ health endpoint يعكس حالة القرارات والموافقات
- [x] جميع الاختبارات تمر (169 passed)

---

## الخطوة التالية: P0.5

بناءً على خارطة الطريق، P0.5 ستركز على:
- **الذاكرة الدائمة** — حفظ المعلومات عبر الجلسات (P1-1 في الخارطة)
- **سجل القرارات المرتبط بالمحادثات** — ربط القرارات بسياق الحوار
- **تدفق موافقة الذاكرة** — أي ذكرة جديدة تحتاج موافقة المؤسسة قبل التخزين
