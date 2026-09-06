# Ameer Extended Senses — حواس أمير الممتدة

## الهدف

إضافة طبقة استشعار قابلة للتوسع تسمح لأمير باستقبال قياسات من حساسات خارج نطاق الحواس البشرية المباشرة، بدءًا بالإشارات الصوتية خارج السمع البشري، ثم الرؤية الحرارية وتحت الحمراء، مع تجهيز دورة حياة العتاد كاملة من لحظة التوصيل حتى التشغيل.

## المبدأ الأساسي

أمير يفصل دائمًا بين ثلاث طبقات:

1. **الرصد:** ما قاسه الحساس فعلًا، مع القيم الخام أو الملخصات، الوقت، معرّف الحساس والثقة إن توفرت.
2. **التحليل:** تصنيف الإشارة أو الصورة، اكتشاف النمط، والمقارنة مع مصادر معروفة عند توفر دليل مناسب.
3. **التفسير:** أي استنتاج عن المصدر يبقى منفصلًا عن القياس، ولا يُقدَّم كحقيقة بلا دليل مستقل.

وجود إشارة أو نمط حراري غير معتاد لا يسمح لأمير بأن ينسبه تلقائيًا إلى إنسان أو حيوان أو جهاز أو روح أو مرض أو نية أو أي سبب آخر.

## الصوت خارج نطاق السمع البشري

- Infrasound: أقل من 20 Hz.
- Audible: من 20 Hz إلى 20 kHz تقريبًا.
- Ultrasound: أعلى من 20 kHz.

يمكن لأمير إنشاء **تمثيل مسموع** لإشارة فوق صوتية عبر تحويل ترددي مناسب. هذا التمثيل أداة للاستماع والتحليل، وليس ادعاءً بأن الصوت المحوّل هو التردد الفيزيائي الأصلي.

## الرؤية الممتدة والحرارية

تدخل جميعها تحت `Extended Vision` داخل طبقة الحواس الممتدة:

- **LWIR**: تصوير حراري طويل الموجة.
- **MWIR**: تصوير تحت أحمر متوسط الموجة.
- **Radiometric Thermal**: تصوير حراري يعطي قياسات درجة حرارة فعلية بحسب الحساس والمعايرة.
- **NIR**: تحت أحمر قريب؛ رؤية انعكاسية وليست قياس حرارة مباشرًا.
- **SWIR**: تحت أحمر قصير الموجة؛ مفيد لبعض المواد والرطوبة والتمييز الطيفي، لكنه ليس قياس حرارة مباشرًا.
- **Thermal + RGB Fusion**: دمج صورة عادية مع طبقة حرارية/تحت حمراء مع الحفاظ على مصدر كل طبقة.
- **Temporal Thermal Tracking**: متابعة التغير الحراري عبر الزمن.

## طبقة العتاد

التنفيذ الجاهز موجود في `06_Code/kernel/sensor_hardware.py` ويجعل رحلة الجهاز:

`Discover → Identify → Install → Adapt → Connect → Health Check → Operate → Stop`

### المكونات

- `DetectedDevice`: يمثل الجهاز الخام كما اكتشفه النظام، مع USB IDs أو serial أو transport والـmetadata.
- `HardwareProbe`: واجهة اكتشاف الأجهزة المتصلة من نظام التشغيل أو الـedge box.
- `SensorAdapterFactory`: قاعدة معرفة بالموديلات المدعومة؛ تتعرف على الجهاز وتحدد الشركة والموديل والنوع وتبني الـAdapter الصحيح.
- `InstallationRecipe`: وصف متطلبات الدرايفر/SDK الخاصة بالموديل.
- `DriverInstaller`: منفذ تثبيت مقيد؛ يفحص هل المتطلبات موجودة ثم يثبت الدرايفر أو SDK عند الحاجة.
- `SensorDescriptor`: هوية الحساس بعد اعتماده، النوع، الشركة، الموديل، وسيلة الاتصال والقدرات.
- `SensorFrame`: إطار قياس موحد مع timestamp وsequence وpayload ووحدات القياس والـmetadata.
- `SensorAdapter`: واجهة موحدة للتعامل مع SDK/USB/Ethernet/Serial/I2C/SPI/RTSP.
- `SensorHub`: تسجيل الحساسات، connect/disconnect، القراءة، وhealth snapshot.
- `HardwareProvisioner`: المنسق الذي ينفذ الرحلة كاملة تلقائيًا من الاكتشاف حتى الجاهزية والتشغيل.

## ما يستطيع أمير فعله عند شبك جهاز

1. يفحص الأجهزة الجديدة عبر `HardwareProbe`.
2. يقرأ `vendor_id/product_id/serial/transport` أو هوية الشبكة بحسب نوع الاتصال.
3. يطابق الجهاز مع `SensorAdapterFactory` مناسب ويعرف **الشركة والموديل والنوع**.
4. يحدد وصفة التثبيت المطلوبة للموديل.
5. يفحص وجود الدرايفر وSDK؛ وإذا كانا غير موجودين يستخدم `DriverInstaller` لتثبيتهما.
6. ينشئ الـAdapter الصحيح للموديل.
7. يسجل الحساس داخل `SensorHub`.
8. يتصل بالجهاز ويجري health check.
9. يعتبره `ready` فقط إذا نجح الاتصال وحالته سليمة.
10. يشغله ويقرأ `SensorFrame` موحدًا، ثم يمرر البيانات إلى `ExtendedSenses` للتحليل.
11. يستطيع إيقاف الجهاز وفصل الاتصال عبر نفس الطبقة.

إضافة موديل جديد لا تتطلب تعديل قلب أمير؛ المطلوب فقط Factory/Adapter ووصفة تثبيت خاصة بالموديل.

## مصفوفة العتاد الجاهزة للربط

| الفئة | النوع داخل أمير | وسائل الربط المتوقعة | ما يرسله الـAdapter |
|---|---|---|---|
| صوت فوق سمعي | `ultrasonic_audio` | USB / ADC / SDK | frequency, dB, duration, sample rate |
| صوت تحت سمعي | `infrasound_audio` | USB / ADC / Serial | frequency, dB, duration, sample rate |
| حراري Radiometric | `thermal_radiometric` | USB / Ethernet / SDK / RTSP+metadata | min/max/mean °C, hotspots, frame metadata |
| حراري LWIR | `thermal_lwir` | USB / Ethernet / SDK | image/intensity frame |
| حراري MWIR | `thermal_mwir` | Ethernet / vendor SDK | image/intensity frame |
| NIR | `nir_camera` | USB / CSI / Ethernet | image/intensity frame |
| SWIR | `swir_camera` | USB3 / GigE / vendor SDK | image/intensity frame |
| RGB | `rgb_camera` | USB / RTSP / CSI | image frame/reference |
| اهتزاز | `vibration` | I2C / SPI / Serial / USB | frequency/amplitude |

## قواعد التثبيت والتشغيل

- التثبيت لا يعتمد على أوامر عشوائية داخل طبقة الحساس؛ كل موديل يملك `InstallationRecipe` محددة، وينفذها backend مسؤول عن نظام التشغيل.
- قبل أي إعادة تثبيت يتم فحص `is_installed()` لتجنب العبث ببيئة سليمة.
- تعريف الجهاز مبني على هوية فعلية من النظام، وليس تخمينًا من اسم يدوي.
- بعد التثبيت لا يعتبر الجهاز صالحًا حتى ينجح `connect` و`health`.
- بيانات القياس تمر بصيغة موحدة حتى لا تعتمد طبقة التحليل على شركة مصنعة بعينها.
- عند عدم معرفة الموديل يعيده أمير كـ`unsupported` بدل محاولة تشغيله بمحول خاطئ.

## قواعد اختيار العتاد لاحقًا

1. SDK موثق أو بروتوكول مفتوح، بدل برنامج مغلق لا يخرج البيانات.
2. إمكانية قراءة raw/radiometric data، وليس فقط لقطة شاشة ملوّنة.
3. timestamps أو frame sequence موثوقة للمزامنة بين الحساسات.
4. دعم Linux/Windows بحسب جهاز أمير الميداني.
5. للحراري: توفر emissivity/calibration metadata مهم للقياس الدقيق.
6. للصوت فوق السمعي: bandwidth ومعدل عينة فعليان يغطيان النطاق المطلوب.
7. عند دمج Thermal + RGB: يفضّل مزامنة hardware أو timestamps جيدة ومعلمات lens/FOV معروفة.

## الحالة الحالية

**Software analysis layer:** implemented for acoustic + extended vision observations.

**Hardware integration layer:** implemented and device-agnostic.

**Discovery/model identification/install/connect/operate lifecycle:** implemented as a reusable framework.

**Device-specific drivers/adapters:** تُضاف عند تحديد الموديل الفعلي؛ وقتها تتم إضافة Factory/Adapter/InstallationRecipe للموديل، وليس إعادة بناء النظام.

## واجهة نظام الظل المقترحة

بطاقة **الحواس الممتدة** تعرض:
- «تم اكتشاف جهاز جديد» مع الشركة والموديل ووسيلة الربط.
- حالة الدرايفر/SDK: موجود / جارٍ التثبيت / جاهز / خطأ.
- الحساسات المسجلة والمتصلة وحالتها.
- health لكل حساس وأخطاء الاتصال إن وجدت.
- النطاق الحالي: Ultrasound / Infrasound / LWIR / MWIR / NIR / SWIR / Radiometric.
- القياسات الخام والملخص المفهوم.
- Thermal hotspot + min/max/mean عندما تكون الكاميرا radiometric.
- Overlay حراري + RGB عند توفر المعايرة المكانية.
- سجل زمني للأحداث والتغييرات.
- درجة الثقة، مع فصل واضح بين «مرصود» و«تفسير محتمل».

بهذا تكون البنية مجهزة بحيث إذا شبكنا جهازًا مدعومًا، أمير يستطيع **التعرف عليه، تجهيز متطلباته، توصيله، اختباره، استخدامه وتشغيله** ضمن نفس منظومة الحواس الممتدة.
