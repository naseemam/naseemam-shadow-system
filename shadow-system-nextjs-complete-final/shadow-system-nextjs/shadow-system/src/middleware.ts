import { NextRequest, NextResponse } from 'next/server';
import { verify } from 'jsonwebtoken';

// مفتاح سري للتوقيع JWT (يجب أن يكون في متغيرات البيئة في الإصدار النهائي)
const JWT_SECRET = 'shadow-system-secret-key-2025';

// المسارات التي لا تحتاج إلى مصادقة
const publicPaths = ['/login', '/api/auth/login', '/api/auth/check'];

export function middleware(request: NextRequest) {
  // التحقق مما إذا كان المسار عاماً
  const path = request.nextUrl.pathname;
  if (publicPaths.some(publicPath => path.startsWith(publicPath))) {
    return NextResponse.next();
  }

  // الحصول على ملف تعريف الارتباط
  const token = request.cookies.get('auth_token')?.value;

  // إذا لم يكن هناك رمز، إعادة توجيه إلى صفحة تسجيل الدخول
  if (!token) {
    const url = new URL('/login', request.url);
    url.searchParams.set('from', request.nextUrl.pathname);
    return NextResponse.redirect(url);
  }

  try {
    // التحقق من صحة الرمز
    verify(token, JWT_SECRET);
    return NextResponse.next();
  } catch (error) {
    // رمز غير صالح، إعادة توجيه إلى صفحة تسجيل الدخول
    const url = new URL('/login', request.url);
    url.searchParams.set('from', request.nextUrl.pathname);
    return NextResponse.redirect(url);
  }
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
};
