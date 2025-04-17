#!/bin/bash

# هذا السكريبت يقوم بتثبيت جميع التبعيات اللازمة للمشروع

echo "جاري تثبيت التبعيات..."

# تثبيت Node.js إذا لم يكن موجوداً
if ! command -v node &> /dev/null; then
  echo "Node.js غير مثبت. جاري التثبيت..."
  curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
  sudo apt-get install -y nodejs
fi

# تثبيت PNPM إذا لم يكن موجوداً
if ! command -v pnpm &> /dev/null; then
  echo "PNPM غير مثبت. جاري التثبيت..."
  npm install -g pnpm
fi

# تثبيت تبعيات المشروع
echo "جاري تثبيت تبعيات المشروع..."
pnpm install

# تثبيت التبعيات الإضافية
echo "جاري تثبيت التبعيات الإضافية..."
pnpm add jsonwebtoken pg @types/jsonwebtoken @types/pg

# إنشاء ملف .env إذا لم يكن موجوداً
if [ ! -f .env ]; then
  echo "جاري إنشاء ملف .env..."
  cp .env.example .env
  echo "تم إنشاء ملف .env. يرجى تعديل القيم حسب إعداداتك."
fi

echo "تم تثبيت جميع التبعيات بنجاح!"
echo "للبدء في استخدام المشروع، قم بتشغيل السكريبت التالي لإعداد قاعدة البيانات:"
echo "bash scripts/setup-db.sh"
echo "ثم قم بتشغيل الخادم المحلي:"
echo "pnpm run dev"
