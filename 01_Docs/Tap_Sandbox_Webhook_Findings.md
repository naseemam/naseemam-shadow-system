# Tap Sandbox webhook findings

المصدر الرسمي: https://developers.tap.company/docs/webhook

أوضحت وثيقة Tap أن webhook هو اتصال server-to-server لتحديث حالة الدفع، وأن endpoint يجب أن يستقبل POST. تعرض أمثلة Tap رأسي `hashstring` و`hash`، وتطلب حساب hashstring من حقول المعاملة ثم مقارنته بالقيمة الواردة.

حقول hashstring لحالات charge/authorize/refund هي: `id`, `amount` بعد التقريب وفق عملة ISO، `currency`, `reference.gateway`, `reference.payment`, `status`, و`transaction.created`. الصيغة الرسمية:

```text
x_id{id}x_amount{amount}x_currency{currency}x_gateway_reference{gateway_reference}x_payment_reference{payment_reference}x_status{status}x_created{created}
```

ثم يحسب النظام `HMAC-SHA256` باستخدام Tap Secret API Key، وتقارن النتيجة بالقيمة الواردة في رأس `hashstring`.

تذكر الوثيقة أيضًا أن Tap قد يعيد المحاولة عند فشل POST، وأن endpoint لا ينبغي أن يعتمد فقط على redirect، لذلك نستخدم `event_id` لمنع إعادة معالجة الحدث.

مصدر إضافي لبيئة الاختبار: https://developers.tap.company/reference/testing-cards
مصدر تدفق البطاقات المشفرة: https://developers.tap.company/docs/encrypted-card-flow-pci
