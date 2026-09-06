# Ameer Extended Senses — حواس أمير الممتدة

## الهدف

إضافة طبقة استشعار قابلة للتوسع تسمح لأمير باستقبال قياسات من حساسات خارج نطاق الحواس البشرية المباشرة، بدءًا بالإشارات الصوتية خارج السمع البشري، ثم الرؤية الحرارية وتحت الحمراء، مع تجهيز دورة حياة العتاد كاملة من لحظة التوصيل حتى التشغيل، ثم عرض الصور والفيديو والصوت والبث المباشر داخل نظام الظل.

## المبدأ الأساسي

أمير يفصل دائمًا بين أربع طبقات:

1. **الرصد:** ما قاسه الحساس فعلًا، مع القيم الخام أو الملخصات، الوقت، معرّف الحساس والثقة إن توفرت.
2. **التحليل:** تصنيف الإشارة أو الصورة، اكتشاف النمط، والمقارنة مع مصادر معروفة عند توفر دليل مناسب.
3. **التفسير:** أي استنتاج عن المصدر يبقى منفصلًا عن القياس، ولا يُقدَّم كحقيقة بلا دليل مستقل.
4. **العرض:** تقديم الدليل الحسي للمستخدم بصيغة صورة أو فيديو أو صوت أو بث مباشر أو مخطط، مع الحفاظ على مصدر كل أصل وبياناته.

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

## طبقة العرض الحسي

التنفيذ موجود في `06_Code/kernel/media_presentation.py` ويضيف واجهة موحّدة لعرض ما رآه أو سمعه أمير داخل نظام الظل بدون ربط الواجهة بموديل حساس معين.

### الأصول المدعومة

- `image`: صورة ثابتة عادية أو حرارية.
- `video`: مقطع مسجل.
- `audio`: تسجيل صوتي خام أو نسخة محوّلة لنطاق مسموع.
- `live_stream`: بث حي من كاميرا أو مصدر صوت/فيديو.
- `waveform`: شكل الموجة الصوتية.
- `spectrogram`: مخطط طيفي للتردد عبر الزمن.
- `thermal_overlay`: طبقة حرارية مدمجة بصريًا فوق RGB.

### المكونات

- `MediaAsset`: هوية الأصل، النوع، مصدر الحساس، URI، MIME type، التوقيت، المدة، الدقة ومعدل العينة عند الحاجة.
- `MediaPresentation`: بطاقة عرض جاهزة للواجهة مع الأصل الرئيسي، الأصول المرتبطة، التعليقات والـcontrols.
- `MediaPresentationBuilder`: ينشئ عروض Image / Video / Audio / Live Stream / Thermal+RGB Fusion.
- `MediaPresentationRegistry`: سجل داخلي للعروض الحالية يمكن ربطه لاحقًا بتخزين دائم أو event bus.

### عناصر التحكم

- الصور: zoom / pan / freeze frame / save snapshot / compare.
- الفيديو: play / pause / seek / speed / freeze frame / save snapshot.
- الصوت: play / pause / seek / volume / speed.
- البث الحي: play / pause / freeze frame / save snapshot.
- Thermal + RGB: toggle RGB / thermal / overlay مع بقاء الطبقات الأصلية منفصلة.

### عرض الصوت فوق السمعي

يمكن لبطاقة صوت واحدة أن تجمع:

1. التسجيل الأصلي إذا كان الحساس يحفظه.
2. النسخة المحوّلة لنطاق مسموع للبشر.
3. waveform.
4. spectrogram.
5. الترددات والـmetadata ودرجة الثقة.

ويجب أن يبقى واضحًا أي ملف هو الأصل وأي ملف هو تحويل للاستماع فقط.

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
11. إذا نتجت صورة/فيديو/صوت/stream، ينشئ لها `MediaAsset` ثم بطاقة `MediaPresentation` قابلة للعرض مباشرة في نظام الظل.
12. يستطيع إيقاف الجهاز وفصل الاتصال عبر نفس الطبقة.

إضافة موديل جديد لا تتطلب تعديل قلب أمير؛ المطلوب فقط Factory/Adapter ووصفة تثبيت خاصة بالموديل.

## مصفوفة العتاد الجاهزة للربط

| الفئة | النوع داخل أمير | وسائل الربط المتوقعة | ما يرسله الـAdapter |
|---|---|---|---|
| صوت فوق سمعي | `ultrasonic_audio` | USB / ADC / SDK | frequency, dB, duration, sample rate, audio ref عند توفره |
| صوت تحت سمعي | `infrasound_audio` | USB / ADC / Serial | frequency, dB, duration, sample rate, audio ref عند توفره |
| حراري Radiometric | `thermal_radiometric` | USB / Ethernet / SDK / RTSP+metadata | min/max/mean °C, hotspots, frame metadata, image/stream ref |
| حراري LWIR | `thermal_lwir` | USB / Ethernet / SDK | image/intensity frame |
| حراري MWIR | `thermal_mwir` | Ethernet / vendor SDK | image/intensity frame |
| NIR | `nir_camera` | USB / CSI / Ethernet | image/intensity frame |
| SWIR | `swir_camera` | USB3 / GigE / vendor SDK | image/intensity frame |
| RGB | `rgb_camera` | USB / RTSP / CSI | image/video/live stream |
| اهتزاز | `vibration` | I2C / SPI / Serial / USB | frequency/amplitude |

## قواعد التثبيت والتشغيل

- التثبيت لا يعتمد على أوامر عشوائية داخل طبقة الحساس؛ كل موديل يملك `InstallationRecipe` محددة، وينفذها backend مسؤول عن نظام التشغيل.
- قبل أي إعادة تثبيت يتم فحص `is_installed()` لتجنب العبث ببيئة سليمة.
- تعريف الجهاز مبني على هوية فعلية من النظام، وليس تخمينًا من اسم يدوي.
- بعد التثبيت لا يعتبر الجهاز صالحًا حتى ينجح `connect` و`health`.
- بيانات القياس تمر بصيغة موحدة حتى لا تعتمد طبقة التحليل على شركة مصنعة بعينها.
- عند عدم معرفة الموديل يعيده أمير كـ`unsupported` بدل محاولة تشغيله بمحول خاطئ.
- طبقة العرض لا تفترض مسار تخزين بعينه؛ URI قد يكون local/object storage/stream endpoint بحسب التنفيذ الفعلي.

## قواعد اختيار العتاد لاحقًا

1. SDK موثق أو بروتوكول مفتوح، بدل برنامج مغلق لا يخرج البيانات.
2. إمكانية قراءة raw/radiometric data، وليس فقط لقطة شاشة ملوّنة.
3. timestamps أو frame sequence موثوقة للمزامنة بين الحساسات.
4. دعم Linux/Windows بحسب جهاز أمير الميداني.
5. للحراري: توفر emissivity/calibration metadata مهم للقياس الدقيق.
6. للصوت فوق السمعي: bandwidth ومعدل عينة فعليان يغطيان النطاق المطلوب.
7. عند دمج Thermal + RGB: يفضّل مزامنة hardware أو timestamps جيدة ومعلمات lens/FOV معروفة.
8. للفيديو والصوت: يفضّل codec/format معروف أو SDK يسمح بالحصول على stream/raw frames بدل الاعتماد على واجهة مغلقة فقط.

## الحالة الحالية

**Software analysis layer:** implemented for acoustic + extended vision observations.

**Hardware integration layer:** implemented and device-agnostic.

**Discovery/model identification/install/connect/operate lifecycle:** implemented as a reusable framework.

**Media presentation layer:** implemented for Image / Video / Audio / Live Stream / Waveform / Spectrogram / Thermal Overlay.

**Device-specific drivers/adapters:** تُضاف عند تحديد الموديل الفعلي؛ وقتها تتم إضافة Factory/Adapter/InstallationRecipe للموديل، وليس إعادة بناء النظام.

**Shadow System rendering/storage endpoints:** تبقى خطوة الربط مع واجهة نظام الظل والتخزين/البث الفعلي؛ عقد البيانات والعرض جاهز مسبقًا.

## واجهة نظام الظل المقترحة

بطاقة **الحواس الممتدة** تعرض:
- «تم اكتشاف جهاز جديد» مع الشركة والموديل ووسيلة الربط.
- حالة الدرايفر/SDK: موجود / جارٍ التثبيت / جاهز / خطأ.
- الحساسات المسجلة والمتصلة وحالتها.
- health لكل حساس وأخطاء الاتصال إن وجدت.
- النطاق الحالي: Ultrasound / Infrasound / LWIR / MWIR / NIR / SWIR / Radiometric.
- الصور مباشرة مع zoom والمقارنة وحفظ لقطة.
- الفيديو المسجل مع play/pause/seek/speed.
- البث الحي مع freeze frame وحفظ لقطة.
- الصوت الخام أو المحوّل مع play/pause/seek/volume/speed.
- waveform + spectrogram بجانب التسجيل الصوتي عند توفرهما.
- Thermal hotspot + min/max/mean عندما تكون الكاميرا radiometric.
- Overlay حراري + RGB مع toggles مستقلة لكل طبقة.
- سجل زمني للأحداث والتغييرات.
- درجة الثقة، مع فصل واضح بين «مرصود» و«تفسير محتمل».

بهذا تكون البنية مجهزة بحيث إذا شبكنا جهازًا مدعومًا، أمير يستطيع **التعرف عليه، تجهيز متطلباته، توصيله، اختباره، استخدامه وتشغيله، ثم عرض الصور والفيديو والصوت والبث الناتج منه** ضمن نفس منظومة الحواس الممتدة.
