import { NextRequest, NextResponse } from 'next/server';
import { sign } from 'jsonwebtoken';
import { getDB } from '@/lib/db';
import { verifyPassword, getJwtSecret } from '@/lib/auth';

interface UserRow {
  id: number;
  username: string;
  password_hash: string;
  role: string;
  display_name: string | null;
}

export async function POST(request: NextRequest) {
  try {
    const { username, password } = await request.json();

    if (!username || !password) {
      return NextResponse.json(
        { success: false, message: 'اسم المستخدم وكلمة المرور مطلوبان' },
        { status: 400 }
      );
    }

    const db = await getDB();
    const user = await db
      .prepare('SELECT id, username, password_hash, role, display_name FROM users WHERE username = ?')
      .bind(username)
      .first<UserRow>();

    if (!user) {
      return NextResponse.json(
        { success: false, message: 'اسم المستخدم أو كلمة المرور غير صحيحة' },
        { status: 401 }
      );
    }

    const valid = await verifyPassword(password, user.password_hash);
    if (!valid) {
      return NextResponse.json(
        { success: false, message: 'اسم المستخدم أو كلمة المرور غير صحيحة' },
        { status: 401 }
      );
    }

    const token = sign(
      { id: user.id, username: user.username, role: user.role },
      getJwtSecret(),
      { expiresIn: '7d' }
    );

    const response = NextResponse.json(
      {
        success: true,
        user: { id: user.id, username: user.username, role: user.role, display_name: user.display_name },
      },
      { status: 200 }
    );

    response.cookies.set({
      name: 'auth_token',
      value: token,
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      maxAge: 60 * 60 * 24 * 7, // 7 days
      path: '/',
    });

    return response;
  } catch (error) {
    console.error('خطأ في تسجيل الدخول:', error);
    return NextResponse.json(
      { success: false, message: 'حدث خطأ أثناء تسجيل الدخول' },
      { status: 500 }
    );
  }
}
