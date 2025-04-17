import { NextRequest, NextResponse } from 'next/server';
import { initializeDatabase } from '@/lib/db';

export async function GET(request: NextRequest) {
  try {
    const result = await initializeDatabase();
    
    if (result.success) {
      return NextResponse.json(
        { success: true, message: 'تم تهيئة قاعدة البيانات بنجاح' },
        { status: 200 }
      );
    } else {
      return NextResponse.json(
        { success: false, message: result.message, error: result.error },
        { status: 500 }
      );
    }
  } catch (error) {
    console.error('خطأ في تهيئة قاعدة البيانات:', error);
    return NextResponse.json(
      { success: false, message: 'حدث خطأ أثناء تهيئة قاعدة البيانات' },
      { status: 500 }
    );
  }
}
