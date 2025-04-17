#!/bin/bash

# هذا السكريبت يقوم بنشر المشروع على Vercel

echo "جاري الإعداد للنشر على Vercel..."

# التحقق من تثبيت Vercel CLI
if ! command -v vercel &> /dev/null; then
  echo "Vercel CLI غير مثبت. جاري التثبيت..."
  npm install -g vercel
fi

# التحقق من تسجيل الدخول إلى Vercel
echo "التحقق من تسجيل الدخول إلى Vercel..."
vercel whoami || vercel login

# بناء المشروع
echo "جاري بناء المشروع..."
pnpm run build

# نشر المشروع على Vercel
echo "جاري نشر المشروع على Vercel..."
vercel --prod

echo "تم نشر المشروع بنجاح على Vercel!"
echo "يمكنك الوصول إلى الموقع من خلال الرابط الذي تم توفيره أعلاه."
