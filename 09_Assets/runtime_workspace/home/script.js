/* Ameer Executive Workspace — Runtime-connected UI */

document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('a[href^="#"]').forEach(link => {
    link.addEventListener('click', event => {
      event.preventDefault();
      const targetId = link.getAttribute('href');
      const target = document.querySelector(targetId);
      if (target) {
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    });
  });

  const chatForm = document.getElementById('chat-form');
  const chatMessage = document.getElementById('chat-message');
  const chatLog = document.getElementById('chat-log');
  const chatConnectionStatus = document.getElementById('chat-connection-status');

  if (chatForm && chatMessage && chatLog) {
    chatForm.addEventListener('submit', async event => {
      event.preventDefault();
      const text = chatMessage.value.trim();
      if (!text) return;

      appendMessage(chatLog, text, 'user');
      chatMessage.value = '';
      chatMessage.focus();

      setConnectionState(chatConnectionStatus, 'جاري الإرسال...');
      try {
        const response = await fetch('/ask', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query: text }),
        });

        if (!response.ok) {
          const errorText = await response.text();
          throw new Error(`HTTP ${response.status} - ${errorText}`);
        }

        const payload = await response.json();
        const ameerReply = extractAmeerReply(payload);
        appendMessage(chatLog, ameerReply, 'ameer');
        setConnectionState(chatConnectionStatus, 'متصل');
      } catch (error) {
        appendMessage(chatLog, 'تعذر الوصول إلى /ask حاليًا. تحقق من تشغيل Runtime.', 'ameer');
        setConnectionState(chatConnectionStatus, 'غير متصل');
        console.error('[Ameer] /ask request failed:', error);
      }
    });
  }

  updateHealthPanel();

  console.log('[Ameer] Executive Workspace runtime integration loaded.');
});

function appendMessage(container, text, role) {
  const message = document.createElement('div');
  message.className = `message ${role}`;
  message.textContent = text;
  container.appendChild(message);
  container.scrollTop = container.scrollHeight;
}

function formatTime(date) {
  return date.toLocaleTimeString('ar-EG', { hour: '2-digit', minute: '2-digit' });
}

function extractAmeerReply(payload) {
  if (!payload || typeof payload !== 'object') return 'تم استلام الطلب.';
  if (typeof payload.reply === 'string' && payload.reply.trim()) return payload.reply.trim();
  if (typeof payload.message === 'string' && payload.message.trim()) return payload.message.trim();
  if (typeof payload.response === 'string' && payload.response.trim()) return payload.response.trim();
  if (typeof payload.answer === 'string' && payload.answer.trim()) return payload.answer.trim();
  return 'تم استلام الطلب، لكن الرد النصي غير متاح بصيغة متوقعة.';
}

async function updateHealthPanel() {
  const updatedAt = document.getElementById('health-updated-at');
  const server = document.getElementById('health-server');
  const documents = document.getElementById('health-documents');
  const brain = document.getElementById('health-brain');
  const memory = document.getElementById('health-memory');
  const projects = document.getElementById('health-projects');

  try {
    const response = await fetch('/health');
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const payload = await response.json();
    const runtime = payload.ameer_status || {};

    setHealthValue(server, runtime.Server);
    setHealthValue(documents, runtime.Documents, payload.documents);
    setHealthValue(brain, runtime.Brain);
    setHealthValue(memory, runtime.Memory);
    setHealthValue(projects, runtime.Projects);

    if (updatedAt) {
      updatedAt.textContent = `آخر تحديث: ${formatTime(new Date())}`;
    }
  } catch (error) {
    setHealthValue(server, 'Offline');
    setHealthValue(documents, 'Unknown');
    setHealthValue(brain, 'Unknown');
    setHealthValue(memory, 'Unknown');
    setHealthValue(projects, 'Unknown');
    if (updatedAt) {
      updatedAt.textContent = 'فشل التحديث';
    }
    console.error('[Ameer] /health request failed:', error);
  }
}

function setHealthValue(element, value, count) {
  if (!element) return;
  const normalized = typeof value === 'string' && value.trim() ? value.trim() : 'Unknown';
  if (typeof count === 'number') {
    element.textContent = `${normalized} (${count})`;
  } else {
    element.textContent = normalized;
  }
  element.classList.toggle('ok', normalized.toLowerCase() === 'ready' || normalized.toLowerCase() === 'online');
  element.classList.toggle('warn', normalized.toLowerCase() !== 'ready' && normalized.toLowerCase() !== 'online');
}

function setConnectionState(element, text) {
  if (!element) return;
  element.textContent = text;
}
