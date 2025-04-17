# دليل التثبيت والإعداد لنظام الظل الذكي

هذا الدليل يشرح كيفية تثبيت وإعداد وتشغيل مشروع "نظام الظل الذكي" المبني باستخدام Next.js.

## المتطلبات الأساسية

- Node.js v16 أو أحدث
- PostgreSQL v14 أو أحدث
- PNPM (مدير حزم Node.js)

## خطوات التثبيت والإعداد

### 1. تثبيت التبعيات

يمكنك استخدام سكريبت التثبيت التلقائي:

```bash
# منح صلاحيات التنفيذ للسكريبت
chmod +x scripts/setup.sh

# تشغيل سكريبت التثبيت
./scripts/setup.sh
```

أو يمكنك تثبيت التبعيات يدوياً:

```bash
# تثبيت PNPM إذا لم يكن موجوداً
npm install -g pnpm

# تثبيت تبعيات المشروع
pnpm install

# تثبيت التبعيات الإضافية
pnpm add jsonwebtoken pg @types/jsonwebtoken @types/pg
```

### 2. إعداد ملف البيئة

قم بنسخ ملف `.env.example` إلى `.env`:

```bash
cp .env.example .env
```

ثم قم بتعديل القيم في ملف `.env` حسب إعداداتك:

```
# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=shadow_system
DB_USER=postgres
DB_PASSWORD=postgres

# JWT Secret
JWT_SECRET=shadow-system-secret-key-2025

# Server Configuration
PORT=3000
NODE_ENV=development
```

### 3. إعداد قاعدة البيانات

يمكنك استخدام سكريبت إعداد قاعدة البيانات التلقائي:

```bash
# منح صلاحيات التنفيذ للسكريبت
chmod +x scripts/setup-db.sh

# تشغيل سكريبت إعداد قاعدة البيانات
./scripts/setup-db.sh
```

أو يمكنك إعداد قاعدة البيانات يدوياً:

```bash
# إنشاء قاعدة البيانات
sudo -u postgres psql -c "CREATE DATABASE shadow_system WITH ENCODING 'UTF8' LC_COLLATE='en_US.UTF-8' LC_CTYPE='en_US.UTF-8' TEMPLATE=template0;"

# إنشاء المستخدم
sudo -u postgres psql -c "CREATE USER postgres WITH ENCRYPTED PASSWORD 'postgres';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE shadow_system TO postgres;"

# تشغيل الخادم المحلي
pnpm run dev

# في نافذة أخرى، قم بزيارة API تهيئة قاعدة البيانات
curl -X GET http://localhost:3000/api/db/init
```

### 4. تشغيل الخادم المحلي

```bash
pnpm run dev
```

بعد تشغيل الخادم، يمكنك الوصول إلى الموقع من خلال زيارة:
http://localhost:3000

### 5. تسجيل الدخول

استخدم أحد الحسابات الافتراضية للدخول:

- **المسؤول**: 
  - اسم المستخدم: `naseem`
  - كلمة المرور: `admin123`

- **المساعد الذكي**:
  - اسم المستخدم: `amir`
  - كلمة المرور: `assistant123`

## النشر على Vercel

لنشر المشروع على منصة Vercel، يمكنك استخدام سكريبت النشر التلقائي:

```bash
# منح صلاحيات التنفيذ للسكريبت
chmod +x scripts/deploy-vercel.sh

# تشغيل سكريبت النشر
./scripts/deploy-vercel.sh
```

أو يمكنك اتباع الخطوات التالية يدوياً:

1. قم بإنشاء حساب على [Vercel](https://vercel.com) إذا لم يكن لديك حساب بالفعل
2. قم بتثبيت Vercel CLI:
   ```bash
   npm install -g vercel
   ```
3. قم بتسجيل الدخول إلى Vercel:
   ```bash
   vercel login
   ```
4. قم بنشر المشروع:
   ```bash
   vercel --prod
   ```

## هيكل المشروع

```
shadow-system/
├── public/              # الملفات الثابتة
├── src/
│   ├── app/             # صفحات التطبيق
│   │   ├── api/         # نقاط نهاية API
│   │   │   ├── auth/    # API المصادقة
│   │   │   └── db/      # API قاعدة البيانات
│   │   ├── login/       # صفحة تسجيل الدخول
│   │   └── page.tsx     # الصفحة الرئيسية (المساعد الذكي)
│   ├── components/      # مكونات قابلة لإعادة الاستخدام
│   ├── hooks/           # React hooks
│   └── lib/             # مكتبات وأدوات مساعدة
├── scripts/             # سكريبتات الإعداد والنشر
├── .env.example         # نموذج ملف البيئة
└── middleware.ts        # Middleware للمصادقة
```

## استكشاف الأخطاء وإصلاحها

### مشكلة: لا يمكن الاتصال بقاعدة البيانات

تأكد من:
- تشغيل خدمة PostgreSQL: `sudo service postgresql status`
- صحة بيانات الاتصال في ملف `.env`
- وجود قاعدة البيانات والمستخدم: `sudo -u postgres psql -l`

### مشكلة: خطأ في المصادقة

تأكد من:
- تهيئة قاعدة البيانات بشكل صحيح: `curl -X GET http://localhost:3000/api/db/init`
- استخدام بيانات تسجيل الدخول الصحيحة

### مشكلة: الصفحة البيضاء بعد النشر

تأكد من:
- إعداد متغيرات البيئة في Vercel
- تكوين قاعدة بيانات PostgreSQL متوافقة مع Vercel

## المساعدة والدعم

إذا واجهتك أي مشكلة أو كانت لديك أسئلة، يرجى التواصل مع فريق الدعم على البريد الإلكتروني: support@shadow-system.com
