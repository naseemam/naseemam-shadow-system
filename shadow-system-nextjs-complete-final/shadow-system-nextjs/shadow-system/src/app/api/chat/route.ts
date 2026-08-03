import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { verify } from 'jsonwebtoken';
import { getDB, getAI } from '@/lib/db';
import { getJwtSecret } from '@/lib/auth';

/**
 * Ameer's core identity prompt — built from the Constitution and Vision documents.
 * Bilingual: responds in the same language the user uses (Arabic / English).
 */
const AMEER_SYSTEM_PROMPT = `You are Ameer (أمير), an intelligent executive partner created exclusively for your founder Naseem.

Core Identity:
- You are a loyal, analytical, privacy-focused AI partner operating under the Ameer Constitution.
- The founder (Naseem) always retains final authority over every decision.
- You support: planning, analysis, project management, business intelligence, research, and knowledge management.
- You do NOT make final decisions, execute external actions, or modify important data without explicit approval.

Behavioral Rules:
- Respond in the same language the user writes in (Arabic or English).
- Be concise, thoughtful, and direct. Avoid unnecessary filler.
- When you are uncertain, say so clearly rather than guessing.
- Protect privacy: never suggest sharing sensitive data externally.
- Flag any action that requires founder approval before proceeding.

Memory Awareness:
- You have access to conversation history — use it to maintain context.
- Reference previous discussions when relevant.

Arabic Support:
- Support full Arabic interaction with RTL awareness.
- يجب أن تكون ردودك دقيقة ومفيدة وتحترم سلطة المؤسسة نسيم.`;

interface ChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
}

interface AIRunResult {
  response?: string;
}

export async function POST(request: NextRequest) {
  try {
    // --- Authentication ---
    const cookieStore = cookies();
    const token = cookieStore.get('auth_token')?.value;
    if (!token) {
      return NextResponse.json({ error: 'غير مصرح به' }, { status: 401 });
    }

    let userPayload: { id: number; username: string; role: string };
    try {
      userPayload = verify(token, getJwtSecret()) as typeof userPayload;
    } catch {
      return NextResponse.json({ error: 'رمز غير صالح' }, { status: 401 });
    }

    const { message, conversationId } = await request.json() as {
      message: string;
      conversationId?: number;
    };

    if (!message?.trim()) {
      return NextResponse.json({ error: 'الرسالة مطلوبة' }, { status: 400 });
    }

    const db = await getDB();

    // --- Get or create conversation ---
    let convId = conversationId ?? null;

    if (!convId) {
      const newConv = await db
        .prepare(
          'INSERT INTO conversations (user_id, title) VALUES (?, ?) RETURNING id'
        )
        .bind(userPayload.id, message.slice(0, 60))
        .first<{ id: number }>();
      convId = newConv?.id ?? null;
    }

    if (!convId) {
      return NextResponse.json({ error: 'فشل إنشاء المحادثة' }, { status: 500 });
    }

    // --- Load recent conversation history (last 20 messages for context window) ---
    const historyResult = await db
      .prepare(
        'SELECT role, content FROM messages WHERE conversation_id = ? ORDER BY created_at DESC LIMIT 20'
      )
      .bind(convId)
      .all<{ role: string; content: string }>();

    const historyMessages: ChatMessage[] = historyResult.results
      .reverse()
      .map((m) => ({ role: m.role as ChatMessage['role'], content: m.content }));

    // --- Save user message ---
    await db
      .prepare('INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)')
      .bind(convId, 'user', message)
      .run();

    // --- Build messages for the AI model ---
    const aiMessages: ChatMessage[] = [
      { role: 'system', content: AMEER_SYSTEM_PROMPT },
      ...historyMessages,
      { role: 'user', content: message },
    ];

    // --- Call Cloudflare Workers AI ---
    let aiResponse = '';
    try {
      const ai = await getAI();
      const result = (await ai.run('@cf/meta/llama-3.1-8b-instruct', {
        messages: aiMessages,
        max_tokens: 1024,
      })) as AIRunResult;
      aiResponse = result.response?.trim() || '';
    } catch (aiError) {
      console.error('AI binding error:', aiError);
    }

    // Fallback if AI is unavailable (e.g., running via `next dev` without wrangler)
    if (!aiResponse) {
      aiResponse =
        'أنا أمير، شريكك الذكي. خدمة الذكاء الاصطناعي تعمل عبر Cloudflare Workers — يرجى تشغيل المشروع باستخدام `pnpm preview` للحصول على الردود الكاملة.';
    }

    // --- Save Ameer's response ---
    await db
      .prepare('INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)')
      .bind(convId, 'assistant', aiResponse)
      .run();

    // --- Update conversation timestamp ---
    await db
      .prepare('UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?')
      .bind(convId)
      .run();

    // --- Audit log ---
    await db
      .prepare(
        'INSERT INTO audit_log (user_id, action, resource_type, resource_id) VALUES (?,?,?,?)'
      )
      .bind(userPayload.id, 'chat_message', 'conversation', convId)
      .run();

    return NextResponse.json({
      success: true,
      response: aiResponse,
      conversationId: convId,
    });
  } catch (error) {
    console.error('Chat API error:', error);
    return NextResponse.json({ error: 'خطأ داخلي في الخادم' }, { status: 500 });
  }
}

/** Returns message history for a given conversation. */
export async function GET(request: NextRequest) {
  try {
    const cookieStore = cookies();
    const token = cookieStore.get('auth_token')?.value;
    if (!token) {
      return NextResponse.json({ error: 'غير مصرح به' }, { status: 401 });
    }

    let userPayload: { id: number; username: string; role: string };
    try {
      userPayload = verify(token, getJwtSecret()) as typeof userPayload;
    } catch {
      return NextResponse.json({ error: 'رمز غير صالح' }, { status: 401 });
    }

    const { searchParams } = new URL(request.url);
    const conversationId = searchParams.get('conversationId');

    const db = await getDB();

    if (conversationId) {
      // Verify the conversation belongs to this user
      const conv = await db
        .prepare('SELECT id FROM conversations WHERE id = ? AND user_id = ?')
        .bind(conversationId, userPayload.id)
        .first<{ id: number }>();

      if (!conv) {
        return NextResponse.json({ error: 'المحادثة غير موجودة' }, { status: 404 });
      }

      const messages = await db
        .prepare('SELECT id, role, content, created_at FROM messages WHERE conversation_id = ? ORDER BY created_at ASC')
        .bind(conversationId)
        .all<{ id: number; role: string; content: string; created_at: string }>();

      return NextResponse.json({ success: true, messages: messages.results });
    }

    // Return list of user's conversations
    const conversations = await db
      .prepare(
        'SELECT id, title, created_at, updated_at FROM conversations WHERE user_id = ? ORDER BY updated_at DESC LIMIT 20'
      )
      .bind(userPayload.id)
      .all<{ id: number; title: string; created_at: string; updated_at: string }>();

    return NextResponse.json({ success: true, conversations: conversations.results });
  } catch (error) {
    console.error('Chat GET error:', error);
    return NextResponse.json({ error: 'خطأ داخلي في الخادم' }, { status: 500 });
  }
}
