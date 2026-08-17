(function () {
  function esc(value) { return String(value || '').replace(/[&<>"']/g, (ch) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[ch])); }
  window.AmeerComponents = window.AmeerComponents || {};
  window.AmeerComponents.friendly_chat = {
    render(container) {
      if (!container) return;
      container.innerHTML = `<section class="module-card" style="display:grid;gap:12px"><div class="dashboard-hero"><div><div class="status-pill">غرفة ودية</div><h2>المحادثة الودية</h2><p>للحديث العام فقط، منفصلة عن غرفة الأعمال والمركز.</p></div><div class="chip">لا تنفيذ</div></div><div data-friendly-log class="dashboard-card"><div class="dashboard-item"><span>ابدأ الحديث هنا.</span></div></div><form data-friendly-form style="display:grid;grid-template-columns:1fr auto;gap:8px"><input data-friendly-input placeholder="اكتب رسالة ودية" autocomplete="off"><button type="submit">إرسال</button></form><div data-friendly-status style="opacity:.7">لا يستدعي هذا القسم العمال ولا يغيّر الملفات.</div></section>`;
      const log = container.querySelector('[data-friendly-log]'); const input = container.querySelector('[data-friendly-input]'); const status = container.querySelector('[data-friendly-status]');
      const add = (who, text) => { const row = document.createElement('div'); row.className = 'dashboard-item'; row.innerHTML = `<div><strong>${who}</strong><div>${esc(text)}</div></div>`; log.appendChild(row); };
      container.querySelector('[data-friendly-form]').addEventListener('submit', async (event) => { event.preventDefault(); const query = input.value.trim(); if (!query) return; add('أنت', query); input.value = ''; status.textContent = 'أمير يرد داخل الغرفة الودية...'; try { const r = await fetch('/friendly-chat', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ query, room: 'friendly' }) }); const data = await r.json(); add('أمير', data.reply || data.message || 'هذه الغرفة للمحادثة الودية فقط.'); status.textContent = data.execution && data.execution.started ? 'يلزم الانتقال إلى غرفة الأعمال.' : 'لم يبدأ أي تنفيذ.'; } catch (_) { add('أمير', 'تعذر الاتصال بالغرفة الودية.'); status.textContent = 'الخادم غير متاح.'; } });
    },
    destroy(container) { if (container) container.innerHTML = ''; }
  };
})();
