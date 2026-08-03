'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';

interface User {
  id: number;
  username: string;
  role: string;
}

interface EventItem {
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

export default function EventsPage() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [events, setEvents] = useState<EventItem[]>([]);
  const [listLoading, setListLoading] = useState(false);
  const [error, setError] = useState('');
  const [actionFilter, setActionFilter] = useState('');
  const router = useRouter();

  const loadEvents = async () => {
    setListLoading(true);
    setError('');
    try {
      const params = new URLSearchParams();
      if (actionFilter.trim()) params.set('action', actionFilter.trim());
      params.set('limit', '100');
      const res = await fetch(`/api/audit?${params.toString()}`);
      const data = await res.json();
      if (!res.ok || !data.success) {
        setError(data.error || 'تعذر تحميل سجل الأحداث');
        return;
      }
      setEvents(Array.isArray(data.events) ? data.events : []);
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
          router.push('/login?from=/events');
          return;
        }
        setUser(data.user);
      } catch {
        router.push('/login?from=/events');
      } finally {
        setLoading(false);
      }
    };
    checkAuth();
  }, [router]);

  useEffect(() => {
    if (user?.role === 'admin') loadEvents();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user]);

  if (loading) {
    return <div className="flex min-h-screen items-center justify-center bg-gray-950 text-gray-300">جاري التحقق...</div>;
  }
  if (!user) return null;

  if (user.role !== 'admin') {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-gray-950 p-6 text-center text-gray-200" dir="rtl">
        <h1 className="text-2xl font-bold">غير مسموح</h1>
        <p className="text-gray-400">هذه الصفحة متاحة للمؤسس فقط.</p>
        <Link href="/" className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">العودة إلى المحادثة</Link>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-950 p-6 text-white" dir="rtl">
      <div className="mx-auto max-w-6xl">
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">سجل الأحداث</h1>
            <p className="mt-1 text-sm text-gray-400">عرض عمليات النظام الأخيرة (قراءة فقط).</p>
          </div>
          <Link href="/" className="rounded-md bg-gray-800 px-4 py-2 text-sm text-gray-200 hover:bg-gray-700">العودة</Link>
        </div>

        {error && (
          <div className="mb-4 rounded-md border border-red-700 bg-red-900/40 px-4 py-3 text-sm text-red-200">{error}</div>
        )}

        <div className="mb-4 flex flex-col gap-2 md:flex-row">
          <input
            value={actionFilter}
            onChange={(e) => setActionFilter(e.target.value)}
            placeholder="فلترة حسب نوع العملية (مثل: memory_)"
            className="flex-1 rounded-md border border-gray-700 bg-gray-800 px-3 py-2 text-sm"
          />
          <button onClick={loadEvents} className="rounded-md bg-blue-600 px-4 py-2 text-sm hover:bg-blue-700">تحديث</button>
        </div>

        {listLoading ? (
          <div className="rounded-lg border border-gray-800 bg-gray-900 p-6 text-center text-gray-400">جاري التحميل...</div>
        ) : events.length === 0 ? (
          <div className="rounded-lg border border-gray-800 bg-gray-900 p-6 text-center text-gray-400">لا توجد أحداث لعرضها.</div>
        ) : (
          <div className="overflow-x-auto rounded-lg border border-gray-800">
            <table className="min-w-full bg-gray-900 text-sm">
              <thead className="bg-gray-800 text-gray-300">
                <tr>
                  <th className="px-3 py-2 text-right">الوقت</th>
                  <th className="px-3 py-2 text-right">المستخدم</th>
                  <th className="px-3 py-2 text-right">العملية</th>
                  <th className="px-3 py-2 text-right">المورد</th>
                  <th className="px-3 py-2 text-right">تفاصيل</th>
                </tr>
              </thead>
              <tbody>
                {events.map((event) => (
                  <tr key={event.id} className="border-t border-gray-800 align-top">
                    <td className="px-3 py-2 text-gray-400">{new Date(event.created_at).toLocaleString('ar-SA')}</td>
                    <td className="px-3 py-2">{event.display_name ?? event.username ?? 'غير معروف'}</td>
                    <td className="px-3 py-2">
                      <span className="rounded bg-blue-900 px-2 py-0.5 text-xs text-blue-300">{event.action}</span>
                    </td>
                    <td className="px-3 py-2 text-gray-300">{event.resource_type ?? '-'} {event.resource_id ? `#${event.resource_id}` : ''}</td>
                    <td className="max-w-md whitespace-pre-wrap px-3 py-2 text-gray-400">{event.details ?? '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
