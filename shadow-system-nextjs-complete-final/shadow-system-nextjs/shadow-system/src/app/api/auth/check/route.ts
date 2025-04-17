import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { verify } from 'jsonwebtoken';

// مفتاح سري للتوقيع JWT (يجب أن يكون في متغيرات البيئة في الإصدار النهائي)
const JWT_SECRET = 'shadow-system-secret-key-2025';

export async function GET(request: NextRequest) {
  try {
    // الحصول على ملف تعريف الارتباط
    const cookieStore = cookies();
    const token = cookieStore.get('auth_token')?.value;

    if (!token) {
      return NextResponse.json(
        { success: false, authenticated: false, message: 'غير مصرح به' },
        { status: 401 }
      );
    }

    // التحقق من صحة الرمز
    try {
      const decoded = verify(token, JWT_SECRET) as {
        id: number;
        username: string;
        role: string;
      };

      return NextResponse.json(
        { 
          success: true, 
          authenticated: true, 
          user: { 
            id: decoded.id, 
            username: decoded.username, 
            role: decoded.role 
          } 
        },
        { status: 200 }
      );
    } catch (error) {
      // رمز غير صالح
      return NextResponse.json(
        { success: false, authenticated: false, message: 'رمز غير صالح' },
        { status: 401 }
      );
    }
  } catch (error) {
    console.error('خطأ في التحقق من المصادقة:', error);
    return NextResponse.json(
      { success: false, message: 'حدث خطأ أثناء التحقق من المصادقة' },
      { status: 500 }
    );
  }
}
