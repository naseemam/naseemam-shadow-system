'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';

interface User {
  id: number;
  username: string;
  role: string;
}

export default function Home() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState('');
  const [chatHistory, setChatHistory] = useState<{ sender: string; text: string; time: string }[]>([]);
  const router = useRouter();

  useEffect(() => {
    // التحقق من حالة المصادقة عند تحميل الصفحة
    const checkAuth = async () => {
      try {
        const response = await fetch('/api/auth/check');
        const data = await response.json();
        
        if (data.authenticated) {
          setUser(data.user);
        } else {
          // إذا كان المستخدم غير مسجل الدخول، إعادة توجيهه إلى صفحة تسجيل الدخول
          router.push('/login');
        }
      } catch (error) {
        console.error('خطأ في التحقق من المصادقة:', error);
        router.push('/login');
      } finally {
        setLoading(false);
      }
    };
    
    checkAuth();
  }, [router]);

  useEffect(() => {
    // إضافة رسائل ترحيبية افتراضية إذا كان المستخدم مسجل الدخول
    if (user) {
      const currentTime = new Date().toLocaleTimeString('ar-SA', { hour: '2-digit', minute: '2-digit' });
      
      if (user.role === 'assistant') {
        setChatHistory([
          { 
            sender: 'system', 
            text: 'مرحباً بك أمير! أنت الآن في وضع المساعد الذكي. يمكنك مساعدة المستخدمين في تحليل البيانات وإدارة المخزون والتعامل مع حالات الطوارئ.', 
            time: currentTime 
          }
        ]);
      } else {
        setChatHistory([
          { 
            sender: 'amir', 
            text: `مرحباً ${user.username}! أنا أمير، المساعد الذكي الخاص بك. كيف يمكنني مساعدتك اليوم؟`, 
            time: currentTime 
          }
        ]);
      }
    }
  }, [user]);

  const handleSendMessage = async () => {
    if (!message.trim()) return;
    
    const currentTime = new Date().toLocaleTimeString('ar-SA', { hour: '2-digit', minute: '2-digit' });
    
    // إضافة رسالة المستخدم إلى المحادثة
    setChatHistory(prev => [
      ...prev, 
      { sender: user?.username || 'guest', text: message, time: currentTime }
    ]);
    
    try {
      // في الإصدار النهائي، هنا سيتم إرسال الرسالة إلى API
      // لكن الآن سنقوم بمحاكاة رد المساعد الذكي بعد ثانية واحدة
      setTimeout(() => {
        let response = '';
        
        if (message.includes('مرحبا') || message.includes('السلام عليكم')) {
          response = 'مرحباً بك! كيف يمكنني مساعدتك اليوم؟';
        } else if (message.includes('تحليل') || message.includes('بيانات') || message.includes('سوق')) {
          response = 'يمكنني مساعدتك في تحليل بيانات السوق وتقديم توصيات بناءً على الاتجاهات الحالية. هل ترغب في تحليل قطاع معين؟';
        } else if (message.includes('مخزون') || message.includes('منتجات')) {
          response = 'لدينا حالياً 1,250 منتجاً في المخزون. هل ترغب في عرض المنتجات منخفضة المخزون أو تقرير حالة المخزون الكامل؟';
        } else if (message.includes('طوارئ') || message.includes('أمان')) {
          response = 'بروتوكولات الأمان محدثة وجاهزة. لم يتم تسجيل أي حالات طوارئ في الأسبوع الماضي.';
        } else if (message.includes('شخصية') || message.includes('ذاكرة')) {
          response = 'يمكنك تخصيص شخصيتي وإضافة ذكريات عاطفية جديدة من خلال قسم إعدادات المساعد الذكي.';
        } else {
          response = 'أفهم ما تقوله. هل يمكنك توضيح كيف يمكنني مساعدتك بشكل أفضل؟';
        }
        
        setChatHistory(prev => [
          ...prev, 
          { 
            sender: user?.role === 'assistant' ? 'user' : 'amir', 
            text: response, 
            time: new Date().toLocaleTimeString('ar-SA', { hour: '2-digit', minute: '2-digit' }) 
          }
        ]);
      }, 1000);
    } catch (error) {
      console.error('خطأ في إرسال الرسالة:', error);
    }
    
    // مسح حقل الرسالة
    setMessage('');
  };

  const handleLogout = async () => {
    try {
      await fetch('/api/auth/logout', { method: 'POST' });
      router.push('/login');
    } catch (error) {
      console.error('خطأ في تسجيل الخروج:', error);
    }
  };

  // إذا كان التحميل جارياً، عرض رسالة التحميل
  if (loading) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center bg-gray-900 p-4">
        <div className="text-center text-white">
          <p className="text-xl">جاري التحميل...</p>
        </div>
      </div>
    );
  }

  // إذا كان المستخدم غير مسجل الدخول، عرض زر تسجيل الدخول
  if (!user) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center bg-gray-900 p-4">
        <div className="w-full max-w-md space-y-8 rounded-lg bg-gray-800 p-8 text-center shadow-lg">
          <h1 className="text-3xl font-bold text-white">نظام الظل الذكي</h1>
          <p className="mt-2 text-gray-300">
            مرحباً بك في نظام الظل الذكي. يرجى تسجيل الدخول للوصول إلى المساعد الذكي "أمير".
          </p>
          <Link 
            href="/login" 
            className="mt-6 block rounded-md bg-blue-600 px-4 py-3 text-center text-lg font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
          >
            تسجيل الدخول
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen flex-col bg-gray-900 text-white" dir="rtl">
      {/* الشريط العلوي */}
      <header className="flex items-center justify-between bg-gray-800 p-4 shadow-md">
        <h1 className="text-xl font-bold">نظام الظل الذكي</h1>
        <div className="flex items-center space-x-4">
          {user && (
            <div className="flex items-center space-x-2 space-x-reverse">
              <span className="text-sm text-gray-300">مرحباً، {user.username}</span>
              <button 
                onClick={handleLogout}
                className="rounded bg-red-600 px-3 py-1 text-sm hover:bg-red-700"
              >
                تسجيل الخروج
              </button>
            </div>
          )}
        </div>
      </header>

      {/* محتوى الصفحة الرئيسي */}
      <main className="flex flex-1 overflow-hidden">
        {/* الشريط الجانبي */}
        <div className="hidden w-64 bg-gray-800 p-4 md:block">
          <h2 className="mb-4 text-lg font-semibold">القائمة الرئيسية</h2>
          <nav className="space-y-2">
            <a href="#" className="block rounded bg-blue-600 p-2 hover:bg-blue-700">الصفحة الرئيسية</a>
            <a href="#" className="block rounded p-2 hover:bg-gray-700">تحليل السوق</a>
            <a href="#" className="block rounded p-2 hover:bg-gray-700">إدارة المخزون</a>
            <a href="#" className="block rounded p-2 hover:bg-gray-700">بروتوكولات الأمان</a>
            <a href="#" className="block rounded p-2 hover:bg-gray-700">حالات الطوارئ</a>
            {user?.role === 'admin' && (
              <a href="#" className="block rounded p-2 hover:bg-gray-700">إعدادات المساعد الذكي</a>
            )}
          </nav>
          
          {user?.role === 'admin' && (
            <div className="mt-8">
              <h2 className="mb-4 text-lg font-semibold">إعدادات المساعد الذكي</h2>
              <nav className="space-y-2">
                <a href="#" className="block rounded p-2 hover:bg-gray-700">تخصيص الشخصية</a>
                <a href="#" className="block rounded p-2 hover:bg-gray-700">الذاكرة العاطفية</a>
                <a href="#" className="block rounded p-2 hover:bg-gray-700">ترحيل المساعد</a>
              </nav>
            </div>
          )}
        </div>

        {/* منطقة المحادثة */}
        <div className="flex flex-1 flex-col bg-gray-900">
          {/* عنوان المحادثة */}
          <div className="border-b border-gray-700 bg-gray-800 p-4">
            <h2 className="text-lg font-semibold">
              {user?.role === 'assistant' ? 'وضع المساعد الذكي' : 'المحادثة مع أمير'}
            </h2>
          </div>

          {/* محتوى المحادثة */}
          <div className="flex-1 overflow-y-auto p-4">
            <div className="space-y-4">
              {chatHistory.map((chat, index) => (
                <div 
                  key={index} 
                  className={`flex ${chat.sender === user?.username || (user?.role === 'assistant' && chat.sender === 'system') ? 'justify-end' : 'justify-start'}`}
                >
                  <div 
                    className={`max-w-[80%] rounded-lg p-3 ${
                      chat.sender === user?.username || (user?.role === 'assistant' && chat.sender === 'system')
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-700 text-white'
                    }`}
                  >
                    <div className="mb-1 text-sm font-semibold">
                      {chat.sender === user?.username ? 'أنت' : chat.sender === 'amir' ? 'أمير' : chat.sender}
                    </div>
                    <div>{chat.text}</div>
                    <div className="mt-1 text-right text-xs opacity-70">{chat.time}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* مربع إدخال الرسالة */}
          <div className="border-t border-gray-700 bg-gray-800 p-4">
            <div className="flex space-x-2 space-x-reverse">
              <input
                type="text"
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
                placeholder={user?.role === 'assistant' ? "أدخل رداً كمساعد ذكي..." : "اكتب رسالة لأمير..."}
                className="flex-1 rounded-md border border-gray-600 bg-gray-700 p-2 text-white placeholder-gray-400 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
              <button
                onClick={handleSendMessage}
                className="rounded-md bg-blue-600 px-4 py-2 font-medium hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
              >
                إرسال
              </button>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
