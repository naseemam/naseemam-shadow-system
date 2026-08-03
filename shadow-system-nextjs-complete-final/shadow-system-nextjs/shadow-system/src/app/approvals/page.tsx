'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';

interface User {
  id: number;
  username: string;
  role: string;
}

interface MemoryItem {
  id: number;
  memory_type: 'temporary' | 'project' | 'founder' | 'core';
  key: string;
  value: string;
  source: string | null;
  confidence: number;
  approved: number;
  created_at: string;
  updated_at: string;
}

export default function ApprovalsPage() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [items, setItems] = useState<MemoryItem[]>([]);
  const [listLoading, setListLoading] = useState(false);
  const [actionId, setActionId] = useState<number | null>(null);
  const [error, setError] = useState('');
  const router = useRouter();

  const loadPending = async () => {
    setListLoading(true);
    setError('');
    try {
      const res = await fetch('/api/memory?pending=true');
      const data = await res.json();
      if (!res.ok || !data.success) {
        setError(data.error || 'تعذر تحميل طلبات الموافقة');
        return;
      }
      setItems(Array.isArray(data.memory) ? data.memory : []);
    } catch {
      setError('تعذر الاتصال بالخادم');
    } finally {
      setListLoading(false);
    }
  };

  useEffect(() => {
    const checkAuth = async () => {
      try {
        const res = await fetch('/api/auth/check');
        const data = await res.json();
        if (!res.ok || !data.authenticated) {
          router.push('/login?from=/approvals');
          return;
        }
        setUser(data.user);
      } catch {
        router.push('/login?from=/approvals');
      } finally {
        setLoading(false);
      }
    };
    checkAuth();
  }, [router]);

  useEffect(() => {
    if (user?.role === 'admin') {
      loadPending();
    }
  }, [user]);

  const handleDecision = async (id: number, approved: 1 | -1) => {
    if (actionId) return;
    setActionId(id);
    setError('');
    try {
      const res = await fetch('/api/memory', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id, approved }),
      });
      const data = await res.json();
      if (!res.ok || !data.success) {
        setError(data.error || 'فشلت العملية');
        return;
      }
      setItems((prev) => prev.filter((item) => item.id !== id));
    } catch {
      setError('تعذر الاتصال بالخادم');
    } finally {
      setActionId(null);
    }
  };

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-950 text-gray-300">
        جاري التحقق...
      </div>
    );
  }

  if (!user) return null;

  if (user.role !== 'admin') {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-gray-950 p-6 text-center text-gray-200" dir="rtl">
        <h1 className="text-2xl font-bold">غير مسموح</h1>
        <p className="text-gray-400">هذه الصفحة متاحة للمؤسس فقط.</p>
        <Link href="/" className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">
          العودة إلى المحادثة
        </Link>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-950 p-6 text-white" dir="rtl">
      <div className="mx-auto max-w-5xl">
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">صفحة الموافقات</h1>
            <p className="mt-1 text-sm text-gray-400">مراجعة واعتماد الذاكرات المعلقة.</p>
          </div>
          <Link href="/" className="rounded-md bg-gray-800 px-4 py-2 text-sm text-gray-200 hover:bg-gray-700">
            العودة
          </Link>
        </div>

        {error && (
          <div className="mb-4 rounded-md border border-red-700 bg-red-900/40 px-4 py-3 text-sm text-red-200">
            {error}
          </div>
        )}

        <div className="mb-4 flex items-center justify-between">
          <p className="text-sm text-gray-400">الطلبات المعلقة: {items.length}</p>
          <button
            onClick={loadPending}
            disabled={listLoading}
            className="rounded-md bg-blue-600 px-3 py-1.5 text-sm hover:bg-blue-700 disabled:opacity-50"
          >
            {listLoading ? 'جاري التحديث...' : 'تحديث'}
          </button>
        </div>

        {listLoading ? (
          <div className="rounded-lg border border-gray-800 bg-gray-900 p-6 text-center text-gray-400">
            جاري تحميل الطلبات...
          </div>
        ) : items.length === 0 ? (
          <div className="rounded-lg border border-gray-800 bg-gray-900 p-6 text-center text-gray-400">
            لا توجد طلبات موافقة معلقة.
          </div>
        ) : (
          <div className="space-y-4">
            {items.map((item) => (
              <div key={item.id} className="rounded-lg border border-gray-800 bg-gray-900 p-4">
                <div className="mb-3 flex items-center justify-between gap-3">
                  <div className="flex items-center gap-2">
                    <span className="rounded-full bg-blue-900 px-2 py-0.5 text-xs text-blue-300">{item.memory_type}</span>
                    <span className="text-xs text-gray-500">#{item.id}</span>
                  </div>
                  <span className="text-xs text-gray-500">{new Date(item.created_at).toLocaleString('ar-SA')}</span>
                </div>
                <p className="mb-2 text-sm text-gray-400">المفتاح: <span className="text-gray-200">{item.key}</span></p>
                <p className="mb-2 whitespace-pre-wrap rounded-md bg-gray-800 p-3 text-sm text-gray-100">{item.value}</p>
                <p className="mb-4 text-xs text-gray-500">
                  المصدر: {item.source ?? 'غير محدد'} • الثقة: {item.confidence}
                </p>

                <div className="flex gap-2">
                  <button
                    onClick={() => handleDecision(item.id, 1)}
                    disabled={actionId === item.id}
                    className="rounded-md bg-green-600 px-3 py-1.5 text-sm text-white hover:bg-green-700 disabled:opacity-50"
                  >
                    موافقة
                  </button>
                  <button
                    onClick={() => handleDecision(item.id, -1)}
                    disabled={actionId === item.id}
                    className="rounded-md bg-red-600 px-3 py-1.5 text-sm text-white hover:bg-red-700 disabled:opacity-50"
                  >
                    رفض
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
