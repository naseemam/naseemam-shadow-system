(function () {
  function esc(value) {
    return String(value || '').replace(/[&<>"']/g, (ch) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[ch]));
  }
  function createFriendlyModule() {
    const messages = [];
    return {
      render(container) {
        if (!container) return;
        container.innerHTML = `
          <section class="module-card" style="display:grid;gap:12px;">
            <div class="dashboard-hero"><div><div class="status-pill">غرفة ودية</div><h2>المحادثة الودية</h2><p>مساحة مستقلة للحديث العام والاستفسارات غير التنفيذية.</p></div><div class="chip">لا تنفيذ</div></div>
            <div class="dashboard-card" data-friendly-messages><div class="dashboard-item"><span>ابدأ الحديث هنا. لن تتحول الرسائل الودية إلى مهام أو أوامر.</span></div></div>
            <form data-friendly-form style="display:grid;grid-template-columns:1fr auto;gap:8px;"><input data-friendly-input aria-label="رسالة ودية" placeholder="اكتب رسالتك الودية هنا" autocomplete="off"><button type="submit">إرسال</button></form>
            <div data-friendly-status style="opacity:.7;font-size:.9em">الغرفة الودية لا تستدعي العمال ولا تغيّر الملفات.</div>
          </section>`;
        const host = container.querySelector('[data-friendly-messages]');
        const input = container.querySelector('[data-friendly-input]');
        const status = container.querySelector('[data-friendly-status]');
        const renderMessages = () => { host.innerHTML = messages.length ? messages.map((m) => `<div class="dashboard-item"><div><strong>${m.role === 'user' ? 'أنت' : 'أمير'}</strong><div>${esc(m.text)}</div></div></div>`).join('') : '<div class="dashboard-item"><span>ابدأ الحديث هنا. لن تتحول الرسائل الودية إلى مهام أو أوامر.</span></div>'; };
        container.querySelector('[data-friendly-form]').addEventListener('submit', async (event) => {
          event.preventDefault(); const text = input.value.trim(); if (!text) return;
          messages.push({ role: 'user', text }); renderMessages(); input.value = ''; status.textContent = 'أمير يرد داخل الغرفة الودية...';
          try { const response = await fetch('/friendly-chat', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ query: text, room: 'friendly' }) }); const data = await response.json(); messages.push({ role: 'assistant', text: data.reply || data.message || 'هذه الغرفة مخصصة للمحادثة الودية فقط.' }); status.textContent = data.execution?.started ? 'تنبيه: راجع الغرفة الصحيحة.' : 'لم يبدأ أي تنفيذ.'; renderMessages(); }
          catch (error) { messages.push({ role: 'assistant', text: 'تعذر الاتصال بالغرفة الودية.' }); status.textContent = 'الخادم غير متاح حاليًا.'; renderMessages(); }
        });
      },
      destroy(container) { if (container) container.innerHTML = ''; }
    };
  }
  window.AmeerWorkspaceModules = window.AmeerWorkspaceModules || {};
  window.AmeerWorkspaceModules['friendly-chat'] = createFriendlyModule();
})();
