import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { verify } from 'jsonwebtoken';
import { getDB } from '@/lib/db';
import { getJwtSecret } from '@/lib/auth';

interface AuditRow {
  id: number;
  user_id: number | null;
  action: string;
  resource_type: string | null;
  resource_id: number | null;
  details: string | null;
  created_at: string;
  username: string | null;
  display_name: string | null;
}

export async function GET(request: NextRequest) {
  try {
    const cookieStore = cookies();
    const token = cookieStore.get('auth_token')?.value;
    if (!token) return NextResponse.json({ error: 'غير مصرح به' }, { status: 401 });

    let user: { id: number; username: string; role: string };
    try {
      user = verify(token, getJwtSecret()) as typeof user;
    } catch {
      return NextResponse.json({ error: 'رمز غير صالح' }, { status: 401 });
    }

    if (user.role !== 'admin') {
      return NextResponse.json({ error: 'هذه العملية تتطلب صلاحيات المؤسس' }, { status: 403 });
    }

    const { searchParams } = new URL(request.url);
    const action = searchParams.get('action');
    const limitParam = Number(searchParams.get('limit') ?? 100);
    const limit = Number.isFinite(limitParam) && limitParam > 0 ? Math.min(limitParam, 200) : 100;

    const db = await getDB();
    let query = `
      SELECT a.id, a.user_id, a.action, a.resource_type, a.resource_id, a.details, a.created_at,
             u.username, u.display_name
      FROM audit_log a
      LEFT JOIN users u ON u.id = a.user_id
      WHERE 1=1
    `;
    const bindings: unknown[] = [];

    if (action) {
      query += ' AND a.action LIKE ?';
      bindings.push(`%${action}%`);
    }

    query += ' ORDER BY a.created_at DESC LIMIT ?';
    bindings.push(limit);

    const stmt = db.prepare(query);
    const rows = await (bindings.length > 0 ? stmt.bind(...bindings) : stmt).all<AuditRow>();

    return NextResponse.json({ success: true, events: rows.results });
  } catch (error) {
    console.error('Audit GET error:', error);
    return NextResponse.json({ error: 'خطأ داخلي في الخادم' }, { status: 500 });
  }
}
