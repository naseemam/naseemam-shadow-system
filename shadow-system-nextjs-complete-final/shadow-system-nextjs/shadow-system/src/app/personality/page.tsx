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
  value: string;
  approved: number;
  created_at: string;
}

export default function PersonalityPage() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [currentPrompt, setCurrentPrompt] = useState('');
  const [draftPrompt, setDraftPrompt] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const router = useRouter();

  const loadCurrent = async () => {
    setError('');
    try {
      const res = await fetch('/api/memory?type=core&key=assistant_personality');
      const data = await res.json();
      if (!res.ok || !data.success) {
        setError(data.error || 'تعذر تحميل الإعداد الحالي');
        return;
      }
      const list = (Array.isArray(data.memory) ? data.memory : []) as MemoryItem[];
      const approved = list.find((item) => item.approved === 1);
      const latest = approved ?? list[0];
      const value = latest?.value ?? '';
      setCurrentPrompt(value);
      setDraftPrompt(value);
    } catch {
      setError('تعذر الاتصال بالخادم');
    }
  };

  useEffect(() => {
    const checkAuth = async () => {
      try {
        const res = await fetch('/api/auth/check');
        const data = await res.json();
        if (!res.ok || !data.authenticated) {
          router.push('/login?from=/personality');
          return;
        }
        setUser(data.user);
      } catch {
        router.push('/login?from=/personality');
      } finally {
        setLoading(false);
      }
    };
    checkAuth();
  }, [router]);

  useEffect(() => {
    if (user?.role === 'admin') loadCurrent();
  }, [user]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (saving) return;
    if (!draftPrompt.trim()) {
      setError('نص الشخصية مطلوب');
      return;
    }

    setSaving(true);
    setMessage('');
    setError('');
    try {
      const res = await fetch('/api/memory', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          memory_type: 'core',
          key: 'assistant_personality',
          value: draftPrompt.trim(),
          source: 'personality_page',
          confidence: 1,
        }),
      });
      const data = await res.json();
      if (!res.ok || !data.success) {
        setError(data.error || 'فشل حفظ التخصيص');
        return;
      }
      setMessage(data.message || 'تم إنشاء تحديث للشخصية');
      await loadCurrent();
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
      <div className="mx-auto max-w-4xl">
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">تخصيص شخصية أمير</h1>
            <p className="mt-1 text-sm text-gray-400">إعداد بسيط عبر الذاكرة الأساسية (Core Memory).</p>
          </div>
          <Link href="/" className="rounded-md bg-gray-800 px-4 py-2 text-sm text-gray-200 hover:bg-gray-700">العودة</Link>
        </div>

        {(error || message) && (
          <div className={`mb-4 rounded-md px-4 py-3 text-sm ${error ? 'border border-red-700 bg-red-900/40 text-red-200' : 'border border-green-700 bg-green-900/30 text-green-200'}`}>
            {error || message}
          </div>
        )}

        <div className="mb-4 rounded-md border border-gray-800 bg-gray-900 p-4">
          <h2 className="mb-2 text-sm font-medium text-gray-300">الإعداد الحالي</h2>
          <p className="whitespace-pre-wrap text-sm text-gray-400">
            {currentPrompt || 'لا يوجد إعداد معتمد/محفوظ حتى الآن.'}
          </p>
        </div>

        <form onSubmit={handleSubmit} className="rounded-md border border-gray-800 bg-gray-900 p-4">
          <h2 className="mb-2 text-sm font-medium text-gray-300">تحديث الشخصية</h2>
          <textarea
            value={draftPrompt}
            onChange={(e) => setDraftPrompt(e.target.value)}
            rows={10}
            className="w-full rounded-md border border-gray-700 bg-gray-800 px-3 py-2 text-sm"
            placeholder="اكتب تعليمات شخصية أمير هنا..."
          />
          <p className="mt-2 text-xs text-gray-500">ملاحظة: هذا الحفظ يُنشئ عنصر Core وقد يحتاج موافقة عبر صفحة الموافقات.</p>
          <button
            type="submit"
            disabled={saving}
            className="mt-3 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
          >
            {saving ? 'جاري الحفظ...' : 'حفظ التحديث'}
          </button>
        </form>
      </div>
    </div>
  );
}
