/* Ameer Executive Workspace — Prototype logic */

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

  if (chatForm && chatMessage && chatLog) {
    chatForm.addEventListener('submit', event => {
      event.preventDefault();
      const text = chatMessage.value.trim();
      if (!text) return;

      appendMessage(chatLog, text, 'user');

      // Future integration hook:
      // sendToRuntimeApi(text).then(response => appendMessage(chatLog, response, 'ameer'))
      const mockReply = 'تم استلام الأمر. سأقوم بتحديث الحالة بعد مزامنة الـ Runtime.';
      appendMessage(chatLog, mockReply, 'ameer');

      chatMessage.value = '';
      chatMessage.focus();
    });
  }

  const lastSync = document.getElementById('last-sync');
  if (lastSync) {
    const now = new Date();
    lastSync.textContent = `آخر تحديث محلي: ${formatTime(now)}`;
  }

  console.log('[Ameer] Executive Workspace prototype loaded.');
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
