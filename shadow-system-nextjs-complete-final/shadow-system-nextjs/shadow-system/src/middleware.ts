import { NextRequest, NextResponse } from 'next/server';
import { verify } from 'jsonwebtoken';

// المسارات التي لا تحتاج إلى مصادقة
const PUBLIC_PATHS = ['/login', '/api/auth/login', '/api/auth/check'];

export function middleware(request: NextRequest) {
  const path = request.nextUrl.pathname;

  if (PUBLIC_PATHS.some((p) => path.startsWith(p))) {
    return NextResponse.next();
  }

  const token = request.cookies.get('auth_token')?.value;

  if (!token) {
    const url = new URL('/login', request.url);
    url.searchParams.set('from', path);
    return NextResponse.redirect(url);
  }

  const jwtSecret = process.env.JWT_SECRET;
  if (!jwtSecret) {
    console.error('JWT_SECRET is not configured');
    return NextResponse.redirect(new URL('/login', request.url));
  }

  try {
    verify(token, jwtSecret);
    return NextResponse.next();
  } catch {
    const url = new URL('/login', request.url);
    url.searchParams.set('from', path);
    return NextResponse.redirect(url);
  }
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
};

