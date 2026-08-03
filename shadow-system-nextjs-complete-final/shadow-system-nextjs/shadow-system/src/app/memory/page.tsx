'use client';

import { FormEvent, useEffect, useState } from 'react';
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

export default function MemoryPage() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [items, setItems] = useState<MemoryItem[]>([]);
  const [listLoading, setListLoading] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [queryKey, setQueryKey] = useState('');
  const [queryType, setQueryType] = useState<'all' | 'temporary' | 'project' | 'founder' | 'core'>('all');
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({
    memory_type: 'project' as 'temporary' | 'project' | 'founder' | 'core',
    key: '',
    value: '',
    source: 'memory_page',
    confidence: '1',
  });
  const router = useRouter();

  const loadMemory = async () => {
    setListLoading(true);
    setError('');
    try {
      const params = new URLSearchParams();
      if (queryType !== 'all') params.set('type', queryType);
      if (queryKey.trim()) params.set('key', queryKey.trim());
      const url = `/api/memory${params.toString() ? `?${params.toString()}` : ''}`;
      const res = await fetch(url);
      const data = await res.json();
      if (!res.ok || !data.success) {
        setError(data.error || 'تعذر تحميل الذاكرة');
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
          router.push('/login?from=/memory');
          return;
        }
        setUser(data.user);
      } catch {
        router.push('/login?from=/memory');
      } finally {
        setLoading(false);
      }
    };
    checkAuth();
  }, [router]);

  useEffect(() => {
    if (user?.role === 'admin') loadMemory();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user]);

  const handleAddMemory = async (e: FormEvent) => {
    e.preventDefault();
    if (saving) return;
    setSaving(true);
    setError('');
    setMessage('');
    try {
      const res = await fetch('/api/memory', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          memory_type: form.memory_type,
          key: form.key.trim(),
          value: form.value.trim(),
          source: form.source.trim() || undefined,
          confidence: Number(form.confidence || '1'),
        }),
      });
      const data = await res.json();
      if (!res.ok || !data.success) {
        setError(data.error || 'فشل حفظ الذاكرة');
        return;
      }
      setMessage(data.message || 'تم حفظ الذاكرة');
      setForm((prev) => ({ ...prev, key: '', value: '' }));
      await loadMemory();
    } catch {
      setError('تعذر الاتصال بالخادم');
    } finally {
      setSaving(false);
    }
  };

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
            <h1 className="text-2xl font-bold">إدارة الذاكرة</h1>
            <p className="mt-1 text-sm text-gray-400">عرض، بحث، وإضافة عناصر الذاكرة.</p>
          </div>
          <Link href="/" className="rounded-md bg-gray-800 px-4 py-2 text-sm text-gray-200 hover:bg-gray-700">العودة</Link>
        </div>

        {(error || message) && (
          <div className={`mb-4 rounded-md px-4 py-3 text-sm ${error ? 'border border-red-700 bg-red-900/40 text-red-200' : 'border border-green-700 bg-green-900/30 text-green-200'}`}>
            {error || message}
          </div>
        )}

        <form onSubmit={handleAddMemory} className="mb-6 rounded-lg border border-gray-800 bg-gray-900 p-4">
          <h2 className="mb-4 text-lg font-semibold">إضافة ذاكرة جديدة</h2>
          <div className="grid gap-3 md:grid-cols-2">
            <select
              value={form.memory_type}
              onChange={(e) => setForm((prev) => ({ ...prev, memory_type: e.target.value as typeof prev.memory_type }))}
              className="rounded-md border border-gray-700 bg-gray-800 px-3 py-2 text-sm"
            >
              <option value="temporary">temporary</option>
              <option value="project">project</option>
              <option value="founder">founder</option>
              <option value="core">core</option>
            </select>
            <input
              value={form.key}
              onChange={(e) => setForm((prev) => ({ ...prev, key: e.target.value }))}
              placeholder="المفتاح"
              className="rounded-md border border-gray-700 bg-gray-800 px-3 py-2 text-sm"
              required
            />
            <input
              value={form.source}
              onChange={(e) => setForm((prev) => ({ ...prev, source: e.target.value }))}
              placeholder="المصدر (اختياري)"
              className="rounded-md border border-gray-700 bg-gray-800 px-3 py-2 text-sm"
            />
            <input
              value={form.confidence}
              onChange={(e) => setForm((prev) => ({ ...prev, confidence: e.target.value }))}
              type="number"
              min="0"
              max="1"
              step="0.1"
              placeholder="الثقة (0-1)"
              className="rounded-md border border-gray-700 bg-gray-800 px-3 py-2 text-sm"
            />
            <textarea
              value={form.value}
              onChange={(e) => setForm((prev) => ({ ...prev, value: e.target.value }))}
              placeholder="قيمة الذاكرة"
              rows={4}
              className="rounded-md border border-gray-700 bg-gray-800 px-3 py-2 text-sm md:col-span-2"
              required
            />
          </div>
          <button
            type="submit"
            disabled={saving}
            className="mt-3 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
          >
            {saving ? 'جاري الحفظ...' : 'حفظ'}
          </button>
        </form>

        <div className="rounded-lg border border-gray-800 bg-gray-900 p-4">
          <div className="mb-4 flex flex-col gap-2 md:flex-row">
            <input
              value={queryKey}
              onChange={(e) => setQueryKey(e.target.value)}
              placeholder="بحث بالمفتاح"
              className="flex-1 rounded-md border border-gray-700 bg-gray-800 px-3 py-2 text-sm"
            />
            <select
              value={queryType}
              onChange={(e) => setQueryType(e.target.value as typeof queryType)}
              className="rounded-md border border-gray-700 bg-gray-800 px-3 py-2 text-sm"
            >
              <option value="all">كل الأنواع</option>
              <option value="temporary">temporary</option>
              <option value="project">project</option>
              <option value="founder">founder</option>
              <option value="core">core</option>
            </select>
            <button onClick={loadMemory} className="rounded-md bg-blue-600 px-4 py-2 text-sm hover:bg-blue-700">تحديث</button>
          </div>

          {listLoading ? (
            <p className="text-sm text-gray-400">جاري تحميل البيانات...</p>
          ) : items.length === 0 ? (
            <p className="text-sm text-gray-400">لا توجد عناصر مطابقة.</p>
          ) : (
            <div className="space-y-3">
              {items.map((item) => (
                <div key={item.id} className="rounded-md border border-gray-800 bg-gray-950 p-3">
                  <div className="mb-2 flex items-center justify-between gap-2 text-xs text-gray-400">
                    <div className="flex items-center gap-2">
                      <span className="rounded bg-blue-900 px-2 py-0.5 text-blue-300">{item.memory_type}</span>
                      <span>#{item.id}</span>
                      <span className={`rounded px-2 py-0.5 ${item.approved === 1 ? 'bg-green-900 text-green-300' : item.approved === 0 ? 'bg-yellow-900 text-yellow-300' : 'bg-red-900 text-red-300'}`}>
                        {item.approved === 1 ? 'معتمد' : item.approved === 0 ? 'معلق' : 'مرفوض'}
                      </span>
                    </div>
                    <span>{new Date(item.updated_at).toLocaleString('ar-SA')}</span>
                  </div>
                  <p className="text-sm text-gray-300">المفتاح: <span className="text-white">{item.key}</span></p>
                  <p className="my-2 whitespace-pre-wrap rounded bg-gray-900 p-2 text-sm text-gray-100">{item.value}</p>
                  <p className="text-xs text-gray-500">المصدر: {item.source ?? 'غير محدد'} • الثقة: {item.confidence}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
