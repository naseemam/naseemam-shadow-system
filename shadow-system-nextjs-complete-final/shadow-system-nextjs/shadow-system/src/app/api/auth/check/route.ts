import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { verify } from 'jsonwebtoken';
import { getJwtSecret } from '@/lib/auth';

export async function GET(_request: NextRequest) {
  try {
    const cookieStore = cookies();
    const token = cookieStore.get('auth_token')?.value;

    if (!token) {
      return NextResponse.json({ authenticated: false }, { status: 401 });
    }

    const decoded = verify(token, getJwtSecret()) as {
      id: number;
      username: string;
      role: string;
    };

    return NextResponse.json({
      success: true,
      authenticated: true,
      user: { id: decoded.id, username: decoded.username, role: decoded.role },
    });
  } catch {
    return NextResponse.json({ authenticated: false }, { status: 401 });
  }
}
