'use client';

import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';

interface User {
  id: number;
  username: string;
  role: string;
  display_name?: string;
}

interface ChatMessage {
  id?: number;
  role: 'user' | 'assistant' | 'system';
  content: string;
  created_at?: string;
}

export default function Home() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState('');
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);
  const [conversationId, setConversationId] = useState<number | null>(null);
  const [sending, setSending] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const router = useRouter();

  // Scroll to the latest message
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => { scrollToBottom(); }, [chatHistory]);

  // Check auth on mount
  useEffect(() => {
    const checkAuth = async () => {
      try {
        const res = await fetch('/api/auth/check');
        const data = await res.json();
        if (data.authenticated) {
          setUser(data.user);
        } else {
          router.push('/login');
        }
      } catch {
        router.push('/login');
      } finally {
        setLoading(false);
      }
    };
    checkAuth();
  }, [router]);

  // Load conversation history once user is known
  useEffect(() => {
    if (!user) return;

    const loadConversations = async () => {
      try {
        const res = await fetch('/api/chat');
        const data = await res.json();
        if (data.success && data.conversations?.length > 0) {
          const lastConv = data.conversations[0];
          setConversationId(lastConv.id);

          const msgRes = await fetch(`/api/chat?conversationId=${lastConv.id}`);
          const msgData = await msgRes.json();
          if (msgData.success) {
            setChatHistory(msgData.messages.map((m: ChatMessage) => ({
              role: m.role,
              content: m.content,
            })));
            return;
          }
        }
      } catch {
        // no previous conversation — show welcome message
      }

      // Welcome message for new session
      const welcome: ChatMessage = {
        role: 'assistant',
        content: user.role === 'assistant'
          ? 'مرحباً! أنت الآن في وضع المساعد الذكي.'
          : `مرحباً ${user.display_name ?? user.username}! أنا أمير، شريكك الذكي. كيف يمكنني مساعدتك اليوم؟`,
      };
      setChatHistory([welcome]);
    };

    loadConversations();
  }, [user]);

  const handleSendMessage = async () => {
    if (!message.trim() || sending) return;

    const userMessage = message.trim();
    setMessage('');
    setSending(true);

    // Optimistically add user message
    setChatHistory((prev) => [...prev, { role: 'user', content: userMessage }]);

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userMessage, conversationId }),
      });

      const data = await res.json();

      if (data.success) {
        if (data.conversationId && !conversationId) {
          setConversationId(data.conversationId);
        }
        setChatHistory((prev) => [...prev, { role: 'assistant', content: data.response }]);
      } else {
        setChatHistory((prev) => [
          ...prev,
          { role: 'assistant', content: 'عذراً، حدث خطأ. يرجى المحاولة مرة أخرى.' },
        ]);
      }
    } catch {
      setChatHistory((prev) => [
        ...prev,
        { role: 'assistant', content: 'تعذّر الاتصال بالخادم. يرجى التحقق من الاتصال.' },
      ]);
    } finally {
      setSending(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleLogout = async () => {
    await fetch('/api/auth/logout', { method: 'POST' });
    router.push('/login');
  };

  const handleNewConversation = () => {
    setConversationId(null);
    setChatHistory([
      {
        role: 'assistant',
        content: `مرحباً ${user?.display_name ?? user?.username}! محادثة جديدة — كيف يمكنني مساعدتك؟`,
      },
    ]);
  };

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-950">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-500 border-t-transparent" />
          <p className="text-gray-400">جاري التحميل...</p>
        </div>
      </div>
    );
  }

  if (!user) return null;

  return (
    <div className="flex h-screen flex-col bg-gray-950 text-white" dir="rtl">
      {/* Header */}
      <header className="flex items-center justify-between border-b border-gray-800 bg-gray-900 px-6 py-3 shadow-sm">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-blue-600 text-sm font-bold">
            أ
          </div>
          <div>
            <h1 className="text-base font-semibold leading-none">نظام الظل — أمير</h1>
            <p className="mt-0.5 text-xs text-gray-400">شريكك الذكي</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <span className="hidden text-sm text-gray-300 sm:block">
            {user.display_name ?? user.username}
          </span>
          {user.role === 'admin' && (
            <span className="rounded-full bg-blue-900 px-2 py-0.5 text-xs text-blue-300">
              مؤسس
            </span>
          )}
          <button
            onClick={handleLogout}
            className="rounded-md bg-gray-800 px-3 py-1.5 text-sm text-gray-300 hover:bg-gray-700 hover:text-white transition-colors"
          >
            خروج
          </button>
        </div>
      </header>

      {/* Layout */}
      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar */}
        <aside className="hidden w-56 flex-col border-l border-gray-800 bg-gray-900 p-4 md:flex">
          <button
            onClick={handleNewConversation}
            className="mb-4 w-full rounded-md bg-blue-600 px-3 py-2 text-sm font-medium hover:bg-blue-700 transition-colors"
          >
            + محادثة جديدة
          </button>

          <nav className="space-y-1">
            <p className="mb-2 px-2 text-xs font-medium text-gray-500">القائمة</p>
            {[
              { label: 'المحادثة', active: true },
              { label: 'تحليل السوق', active: false },
              { label: 'إدارة المشاريع', active: false },
              { label: 'إدارة المخزون', active: false },
              { label: 'بروتوكولات الأمان', active: false },
            ].map(({ label, active }) => (
              <button
                key={label}
                className={`w-full rounded-md px-3 py-2 text-right text-sm transition-colors ${
                  active
                    ? 'bg-blue-600/20 text-blue-400'
                    : 'text-gray-400 hover:bg-gray-800 hover:text-white'
                }`}
              >
                {label}
              </button>
            ))}
          </nav>

          {user.role === 'admin' && (
            <nav className="mt-6 space-y-1 border-t border-gray-800 pt-4">
              <p className="mb-2 px-2 text-xs font-medium text-gray-500">إعدادات أمير</p>
              {['الذاكرة', 'الموافقات', 'سجل الأحداث', 'تخصيص الشخصية'].map((label) => (
                <button
                  key={label}
                  className="w-full rounded-md px-3 py-2 text-right text-sm text-gray-400 hover:bg-gray-800 hover:text-white transition-colors"
                >
                  {label}
                </button>
              ))}
            </nav>
          )}
        </aside>

        {/* Chat area */}
        <main className="flex flex-1 flex-col overflow-hidden">
          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {chatHistory.map((msg, index) => (
              <div
                key={index}
                className={`flex ${msg.role === 'user' ? 'justify-start' : 'justify-end'}`}
              >
                <div
                  className={`max-w-[75%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                    msg.role === 'user'
                      ? 'bg-gray-800 text-gray-100'
                      : 'bg-blue-600 text-white'
                  }`}
                >
                  <p className="mb-1 text-xs font-medium opacity-70">
                    {msg.role === 'user' ? (user.display_name ?? user.username) : 'أمير'}
                  </p>
                  <p className="whitespace-pre-wrap">{msg.content}</p>
                </div>
              </div>
            ))}

            {sending && (
              <div className="flex justify-end">
                <div className="max-w-[75%] rounded-2xl bg-blue-600/50 px-4 py-3">
                  <p className="text-xs font-medium text-blue-200 mb-1">أمير</p>
                  <div className="flex gap-1">
                    <span className="h-2 w-2 animate-bounce rounded-full bg-white/70 [animation-delay:0ms]" />
                    <span className="h-2 w-2 animate-bounce rounded-full bg-white/70 [animation-delay:150ms]" />
                    <span className="h-2 w-2 animate-bounce rounded-full bg-white/70 [animation-delay:300ms]" />
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <div className="border-t border-gray-800 bg-gray-900 p-4">
            <div className="flex items-end gap-2">
              <textarea
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="اكتب رسالة لأمير... (Enter للإرسال، Shift+Enter لسطر جديد)"
                rows={1}
                className="flex-1 resize-none rounded-xl border border-gray-700 bg-gray-800 px-4 py-3 text-sm text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 max-h-32"
                style={{ minHeight: '48px' }}
              />
              <button
                onClick={handleSendMessage}
                disabled={sending || !message.trim()}
                className="flex h-12 w-12 items-center justify-center rounded-xl bg-blue-600 text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-40 transition-colors"
                aria-label="إرسال"
              >
                <svg className="h-5 w-5 rotate-180" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                </svg>
              </button>
            </div>
            <p className="mt-2 text-center text-xs text-gray-600">
              أمير يعمل بموجب دستور المشروع — القرار النهائي لنسيم دائماً
            </p>
          </div>
        </main>
      </div>
    </div>
  );
}

