import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { sign, verify } from 'jsonwebtoken';

// في الإصدار النهائي، هذا سيكون في قاعدة بيانات
const USERS = [
  { id: 1, username: 'naseem', password: 'admin123', role: 'admin' },
  { id: 2, username: 'amir', password: 'assistant123', role: 'assistant' }
];

// مفتاح سري للتوقيع JWT (يجب أن يكون في متغيرات البيئة في الإصدار النهائي)
const JWT_SECRET = 'shadow-system-secret-key-2025';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { username, password } = body;

    // التحقق من بيانات المستخدم
    const user = USERS.find(u => u.username === username && u.password === password);
    
    if (!user) {
      return NextResponse.json(
        { success: false, message: 'اسم المستخدم أو كلمة المرور غير صحيحة' },
        { status: 401 }
      );
    }

    // إنشاء رمز JWT
    const token = sign(
      { 
        id: user.id, 
        username: user.username, 
        role: user.role 
      },
      JWT_SECRET,
      { expiresIn: '1d' }
    );

    // إعداد الاستجابة مع ملف تعريف الارتباط
    const response = NextResponse.json(
      { 
        success: true, 
        user: { 
          id: user.id, 
          username: user.username, 
          role: user.role 
        } 
      },
      { status: 200 }
    );

    // إضافة ملف تعريف الارتباط
    response.cookies.set({
      name: 'auth_token',
      value: token,
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      maxAge: 60 * 60 * 24, // يوم واحد
      path: '/'
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
