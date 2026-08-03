import { NextRequest, NextResponse } from 'next/server';
import { initializeDatabase } from '@/lib/db';

export async function GET(_request: NextRequest) {
  try {
    const result = await initializeDatabase();
    return NextResponse.json(result, { status: result.success ? 200 : 500 });
  } catch (error) {
    console.error('خطأ في تهيئة قاعدة البيانات:', error);
    return NextResponse.json(
      { success: false, message: 'حدث خطأ أثناء تهيئة قاعدة البيانات' },
      { status: 500 }
    );
  }
}
