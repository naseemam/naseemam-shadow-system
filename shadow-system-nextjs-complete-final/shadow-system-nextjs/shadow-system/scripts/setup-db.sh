#!/bin/bash

# هذا السكريبت يقوم بتهيئة قاعدة البيانات وإنشاء الجداول اللازمة

# التأكد من وجود ملف .env
if [ ! -f .env ]; then
  echo "ملف .env غير موجود. يرجى نسخ .env.example إلى .env وتعديل القيم حسب إعداداتك."
  echo "cp .env.example .env"
  exit 1
fi

# استيراد متغيرات البيئة
source .env

# التحقق من وجود PostgreSQL
if ! command -v psql &> /dev/null; then
  echo "PostgreSQL غير مثبت. يرجى تثبيته أولاً."
  echo "sudo apt-get update && sudo apt-get install -y postgresql postgresql-contrib"
  exit 1
fi

# إنشاء قاعدة البيانات إذا لم تكن موجودة
echo "جاري إنشاء قاعدة البيانات $DB_NAME..."
sudo -u postgres psql -c "CREATE DATABASE $DB_NAME WITH ENCODING 'UTF8' LC_COLLATE='en_US.UTF-8' LC_CTYPE='en_US.UTF-8' TEMPLATE=template0;" || true

# إنشاء المستخدم إذا لم يكن موجوداً
echo "جاري إنشاء مستخدم قاعدة البيانات $DB_USER..."
sudo -u postgres psql -c "CREATE USER $DB_USER WITH ENCRYPTED PASSWORD '$DB_PASSWORD';" || true
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;" || true

# تهيئة الجداول عبر API
echo "جاري تهيئة الجداول..."
curl -X GET http://localhost:$PORT/api/db/init

echo "تم إعداد قاعدة البيانات بنجاح!"
