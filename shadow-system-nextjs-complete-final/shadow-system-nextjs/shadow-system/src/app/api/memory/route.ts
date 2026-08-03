import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { verify } from 'jsonwebtoken';
import { getDB } from '@/lib/db';
import { getJwtSecret } from '@/lib/auth';

type MemoryType = 'temporary' | 'project' | 'founder' | 'core';

interface MemoryRow {
  id: number;
  memory_type: MemoryType;
  key: string;
  value: string;
  source: string | null;
  confidence: number;
  approved: number;
  created_at: string;
  updated_at: string;
}

/** Store a new memory entry (requires founder approval for founder/core types). */
export async function POST(request: NextRequest) {
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

    const { memory_type, key, value, source, confidence } = await request.json() as {
      memory_type: MemoryType;
      key: string;
      value: string;
      source?: string;
      confidence?: number;
    };

    if (!memory_type || !key || !value) {
      return NextResponse.json(
        { error: 'memory_type و key و value مطلوبة' },
        { status: 400 }
      );
    }

    // Per constitution: founder and core memory require explicit approval
    const requiresApproval = memory_type === 'founder' || memory_type === 'core';
    const approved = requiresApproval ? 0 : 1;

    const db = await getDB();
    const result = await db
      .prepare(
        `INSERT INTO memory (memory_type, key, value, source, confidence, approved)
         VALUES (?, ?, ?, ?, ?, ?) RETURNING id`
      )
      .bind(memory_type, key, value, source ?? null, confidence ?? 1.0, approved)
      .first<{ id: number }>();

    await db
      .prepare(
        'INSERT INTO audit_log (user_id, action, resource_type, resource_id, details) VALUES (?,?,?,?,?)'
      )
      .bind(
        user.id,
        'memory_create',
        'memory',
        result?.id ?? null,
        JSON.stringify({ memory_type, key, requires_approval: requiresApproval })
      )
      .run();

    return NextResponse.json({
      success: true,
      id: result?.id,
      requires_approval: requiresApproval,
      message: requiresApproval
        ? 'تم إنشاء الذاكرة — تحتاج إلى موافقة نسيم قبل الاعتماد'
        : 'تم حفظ الذاكرة بنجاح',
    });
  } catch (error) {
    console.error('Memory POST error:', error);
    return NextResponse.json({ error: 'خطأ داخلي في الخادم' }, { status: 500 });
  }
}

/** Retrieve memory entries, optionally filtered by type or key. */
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

    const { searchParams } = new URL(request.url);
    const memoryType = searchParams.get('type') as MemoryType | null;
    const key = searchParams.get('key');
    const pendingOnly = searchParams.get('pending') === 'true';

    // Only admins can read founder/core memory
    const db = await getDB();
    let query =
      'SELECT id, memory_type, key, value, source, confidence, approved, created_at, updated_at FROM memory WHERE superseded_by IS NULL';
    const bindings: unknown[] = [];

    if (user.role !== 'admin') {
      query += " AND memory_type NOT IN ('founder','core')";
    }
    if (memoryType) {
      query += ' AND memory_type = ?';
      bindings.push(memoryType);
    }
    if (key) {
      query += ' AND key LIKE ?';
      bindings.push(`%${key}%`);
    }
    if (pendingOnly) {
      query += ' AND approved = 0';
    }
    query += ' ORDER BY updated_at DESC LIMIT 50';

    const stmt = db.prepare(query);
    const rows = await (bindings.length > 0 ? stmt.bind(...bindings) : stmt).all<MemoryRow>();

    return NextResponse.json({ success: true, memory: rows.results });
  } catch (error) {
    console.error('Memory GET error:', error);
    return NextResponse.json({ error: 'خطأ داخلي في الخادم' }, { status: 500 });
  }
}

/** Approve or reject a pending memory entry (admin only). */
export async function PATCH(request: NextRequest) {
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
      return NextResponse.json(
        { error: 'هذه العملية تتطلب صلاحيات المؤسس' },
        { status: 403 }
      );
    }

    const { id, approved } = await request.json() as { id: number; approved: 1 | -1 };

    if (!id || (approved !== 1 && approved !== -1)) {
      return NextResponse.json(
        { error: 'id و approved (1 موافقة / -1 رفض) مطلوبان' },
        { status: 400 }
      );
    }

    const db = await getDB();
    await db
      .prepare(
        'UPDATE memory SET approved = ?, approved_by = ?, approved_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP WHERE id = ?'
      )
      .bind(approved, user.id, id)
      .run();

    await db
      .prepare(
        'INSERT INTO audit_log (user_id, action, resource_type, resource_id, details) VALUES (?,?,?,?,?)'
      )
      .bind(
        user.id,
        approved === 1 ? 'memory_approve' : 'memory_reject',
        'memory',
        id,
        null
      )
      .run();

    return NextResponse.json({
      success: true,
      message: approved === 1 ? 'تمت الموافقة على الذاكرة' : 'تم رفض الذاكرة',
    });
  } catch (error) {
    console.error('Memory PATCH error:', error);
    return NextResponse.json({ error: 'خطأ داخلي في الخادم' }, { status: 500 });
  }
}
