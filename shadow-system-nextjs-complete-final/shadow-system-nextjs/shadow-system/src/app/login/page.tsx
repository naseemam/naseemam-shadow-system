'use client';

import { useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';

export default function LoginPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    // التحقق من حالة المصادقة عند تحميل الصفحة
    const checkAuth = async () => {
      try {
        const response = await fetch('/api/auth/check');
        const data = await response.json();
        
        if (data.authenticated) {
          // إذا كان المستخدم مسجل الدخول بالفعل، إعادة توجيهه إلى الصفحة الرئيسية
          const from = searchParams.get('from') || '/';
          router.push(from);
        }
      } catch (error) {
        console.error('خطأ في التحقق من المصادقة:', error);
      }
    };
    
    checkAuth();
  }, [router, searchParams]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      // إرسال طلب تسجيل الدخول إلى API
      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ username, password }),
      });
      
      const data = await response.json();
      
      if (response.ok && data.success) {
        // تسجيل الدخول ناجح، إعادة توجيه المستخدم
        const from = searchParams.get('from') || '/';
        router.push(from);
      } else {
        // تسجيل الدخول فاشل، عرض رسالة الخطأ
        setError(data.message || 'فشل تسجيل الدخول');
      }
    } catch (err) {
      setError('حدث خطأ أثناء تسجيل الدخول');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gray-900 p-4">
      <div className="w-full max-w-md space-y-8 rounded-lg bg-gray-800 p-8 shadow-lg">
        <div className="text-center">
          <h1 className="text-3xl font-bold text-white">نظام الظل الذكي</h1>
          <h2 className="mt-2 text-xl text-gray-300">تسجيل الدخول</h2>
        </div>

        {error && (
          <div className="rounded-md bg-red-500 p-3 text-center text-white">
            {error}
          </div>
        )}

        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          <div className="space-y-4 rounded-md shadow-sm">
            <div>
              <label htmlFor="username" className="block text-sm font-medium text-gray-300">
                اسم المستخدم
              </label>
              <input
                id="username"
                name="username"
                type="text"
                required
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="mt-1 block w-full rounded-md border-gray-600 bg-gray-700 p-3 text-white placeholder-gray-400 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                placeholder="أدخل اسم المستخدم"
                dir="rtl"
              />
            </div>
            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-300">
                كلمة المرور
              </label>
              <input
                id="password"
                name="password"
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="mt-1 block w-full rounded-md border-gray-600 bg-gray-700 p-3 text-white placeholder-gray-400 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                placeholder="أدخل كلمة المرور"
                dir="rtl"
              />
            </div>
          </div>

          <div>
            <button
              type="submit"
              disabled={loading}
              className="group relative flex w-full justify-center rounded-md bg-blue-600 px-4 py-3 text-lg font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-70"
            >
              {loading ? 'جاري تسجيل الدخول...' : 'تسجيل الدخول'}
            </button>
          </div>

          <div className="text-center text-sm text-gray-400">
            <p>بيانات الدخول الافتراضية:</p>
            <p className="mt-1">المسؤول: naseem / admin123</p>
            <p>المساعد الذكي: amir / assistant123</p>
          </div>
        </form>
      </div>
    </div>
  );
}
