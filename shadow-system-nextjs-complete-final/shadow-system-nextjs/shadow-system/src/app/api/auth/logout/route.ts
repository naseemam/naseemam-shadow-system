import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';

export async function POST(request: NextRequest) {
  try {
    // مسح ملف تعريف الارتباط الخاص بالمصادقة
    const response = NextResponse.json(
      { success: true, message: 'تم تسجيل الخروج بنجاح' },
      { status: 200 }
    );

    // حذف ملف تعريف الارتباط
    response.cookies.set({
      name: 'auth_token',
      value: '',
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      maxAge: 0, // انتهاء الصلاحية فوراً
      path: '/'
    });

    return response;
  } catch (error) {
    console.error('خطأ في تسجيل الخروج:', error);
    return NextResponse.json(
      { success: false, message: 'حدث خطأ أثناء تسجيل الخروج' },
      { status: 500 }
    );
  }
}
