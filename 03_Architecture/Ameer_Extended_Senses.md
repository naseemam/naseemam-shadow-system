# Ameer Extended Senses — حواس أمير الممتدة

## الهدف

إضافة طبقة استشعار قابلة للتوسع تسمح لأمير باستقبال قياسات من حساسات خارج نطاق الحواس البشرية المباشرة، بدءًا بالإشارات الصوتية خارج السمع البشري، ثم الرؤية الحرارية وتحت الحمراء.

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

- **LWIR**: تصوير حراري طويل الموجة، مناسب لتمييز فروقات الحرارة في كثير من الاستخدامات العامة والصناعية.
- **MWIR**: تصوير تحت أحمر متوسط الموجة، ويحتاج عادة حساسًا وتجهيزًا متخصصًا.
- **Radiometric Thermal**: تصوير حراري يعطي قياسات درجة حرارة فعلية لكل نقطة/منطقة بحسب الحساس والمعايرة.
- **NIR**: تحت أحمر قريب؛ رؤية ممتدة تعتمد أساسًا على الانعكاس، وليست قياس حرارة مباشرًا.
- **SWIR**: تحت أحمر قصير الموجة؛ مفيد لبعض المواد والرطوبة والتمييز الطيفي، لكنه أيضًا ليس قياس حرارة مباشرًا بالمعنى الحراري.
- **Thermal + RGB Fusion**: دمج صورة عادية مع طبقة حرارية/تحت حمراء مع الحفاظ على مصدر كل طبقة وبياناتها.
- **Temporal Thermal Tracking**: متابعة التغير الحراري عبر الزمن لاكتشاف الصعود والانخفاض والأنماط المتكررة.

## المكونات

### 1. Sensor Adapter

واجهة العتاد. مسؤوليتها قراءة حساس حقيقي وإرسال القياسات أو التسجيلات/الإطارات إلى أمير. يمكن إضافة محولات مختلفة دون تغيير طبقة التحليل.

أمثلة:
- Ultrasonic microphone / ADC.
- Infrasound sensor.
- Vibration sensor.
- LWIR / MWIR thermal camera.
- Radiometric thermal camera.
- NIR / SWIR camera.
- RGB camera for registered fusion.
- Air-quality sensor.

### 2. Sensor Hardware Layer

التنفيذ الجاهز موجود في `06_Code/kernel/sensor_hardware.py` ويضيف عقدًا ثابتًا للعتاد قبل شراء أي جهاز محدد:

- `SensorDescriptor`: هوية الحساس، النوع، الشركة، الموديل، وسيلة الاتصال والقدرات.
- `SensorFrame`: إطار قياس موحد مع timestamp وsequence وpayload ووحدات القياس والـmetadata.
- `SensorAdapter`: واجهة موحدة لأي SDK/USB/Ethernet/Serial/I2C/SPI/RTSP device adapter.
- `SensorHub`: تسجيل الحساسات، connect/disconnect، منع التكرار، القراءة، وhealth snapshot.
- `NORMALIZED_PAYLOAD_SCHEMAS`: مفاتيح موحدة للصوت فوق/تحت السمعي، thermal radiometric، LWIR/MWIR، NIR/SWIR، RGB والاهتزاز.

بهذا الشكل لا يحتاج قلب أمير أن يعرف الشركة المصنعة. عند شراء أو شبك الجهاز نكتب محولًا صغيرًا خاصًا به يحقق `SensorAdapter`، ثم يدخل الجهاز مباشرة إلى `SensorHub` وباقي مسار التحليل ثابت.

### 3. ExtendedSenses

التنفيذ موجود في `06_Code/kernel/extended_senses.py` ويشمل حاليًا:
- تصنيف نطاق الإشارة الصوتية.
- التحقق من صحة القياسات.
- إنشاء تمثيل ترددي مسموع للإشارة فوق الصوتية.
- استقبال ملخصات رؤية من LWIR / MWIR / Radiometric / NIR / SWIR / RGB fusion.
- تلخيص مدى درجات الحرارة والنقاط الساخنة عند توفر بيانات radiometric فعلية.
- منع التعامل مع NIR/SWIR على أنها قياس حرارة مباشر.
- حفظ فصل صريح بين القياس ومصدر الإشارة أو النمط غير المثبت.

### 4. Capability Governance

القدرة تحمل الاسم `extended_senses` وتُسجَّل كقدرة `extended` معتمدة من المؤسس، وتعتمد على قدرة `analysis` الموجودة. الدالة `ensure_extended_senses_capability()` تنفذ التسجيل بصورة idempotent ولا تنشئ بطاقة مكررة.

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

## قواعد اختيار العتاد لاحقًا

حتى يكون الجهاز Plug-and-Adapt يفضَّل اختيار جهاز يحقق أكبر قدر ممكن من التالي:

1. SDK موثق أو بروتوكول مفتوح، بدل برنامج مغلق لا يخرج البيانات.
2. إمكانية قراءة raw/radiometric data، وليس فقط لقطة شاشة ملوّنة.
3. timestamps أو frame sequence موثوقة للمزامنة بين الحساسات.
4. دعم Linux إن كان الحساس سيعمل على VPS edge box أو جهاز ميداني؛ وإن كان USB محليًا فيكون له driver ثابت.
5. للحراري: توفر emissivity/calibration metadata مهم عند الحاجة لقياس حرارة دقيق.
6. للصوت فوق السمعي: bandwidth ومعدل عينة فعليان يغطيان النطاق المطلوب؛ البرنامج لا يعوض فلترًا أو ADC لا يلتقط التردد أصلًا.
7. عند دمج Thermal + RGB: يفضّل مزامنة hardware أو timestamps جيدة ومعلمات lens/FOV معروفة.

## الحالة الحالية

**Software analysis layer: implemented for acoustic + extended vision observations.**

**Hardware integration layer: implemented and device-agnostic.**

**Device-specific drivers/adapters: تُضاف عند تحديد الجهاز الفعلي.** أمير لا يدّعي وجود حساس غير موصول، لكن البنية الآن جاهزة لاستقباله وإدارته فور توفر SDK/بروتوكول الجهاز.

## واجهة نظام الظل المقترحة

بطاقة **الحواس الممتدة** تعرض:
- الحساسات المسجلة والمتصلة وحالتها ووسيلة الربط.
- health لكل حساس وأخطاء الاتصال إن وجدت.
- النطاق الحالي: Ultrasound / Infrasound / LWIR / MWIR / NIR / SWIR / Radiometric.
- القياسات الخام والملخص المفهوم.
- Thermal hotspot + min/max/mean عندما تكون الكاميرا radiometric.
- Overlay حراري + RGB عند توفر المعايرة المكانية.
- سجل زمني للأحداث والتغييرات.
- زر للاستماع إلى التمثيل المحول للصوت فوق السمعي.
- درجة الثقة، مع فصل واضح بين «مرصود» و«تفسير محتمل».

## ما يحدث لحظة شبك جهاز فعلي

1. تعريف `SensorDescriptor` للجهاز.
2. إضافة Device Adapter صغير يترجم SDK/البروتوكول إلى `SensorFrame`.
3. تسجيله في `SensorHub`.
4. تشغيل connect + health check.
5. قراءة أول frame والتحقق من الوحدات والـmetadata.
6. تمرير القياسات إلى `ExtendedSenses` للتحليل.
7. إظهار stream/events في نظام الظل.

هذا يعني أن ما سيتبقى عند شراء الحساس ليس إعادة بناء المنظومة، بل فقط **موصل الجهاز نفسه ومعايرته**.
