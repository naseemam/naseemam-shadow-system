(function () {
  function createMemoryModule() {
    let state = {
      note: '',
      items: []
    };

    async function refreshMemory() {
      try {
        const response = await fetch('/memory', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json; charset=utf-8' },
          body: JSON.stringify({ text: state.note || 'تحديث من واجهة الذاكرة' })
        });
        const payload = await response.json();
        if (payload.saved) {
          state.items = [payload.note, ...state.items].slice(0, 5);
        }
      } catch (error) {
        console.error(error);
      }
    }

    return {
      render(container) {
        if (!container) return;
        container.innerHTML = `
          <section class="module-card" style="display:grid;gap:12px;">
            <div class="dashboard-hero">
              <div>
                <div class="status-pill">Memory</div>
                <h2>ذاكرة التشغيل</h2>
                <p>هذا القسم يكتب ملاحظة حقيقية إلى ملف الذاكرة المحلي.</p>
              </div>
              <div class="chip">محدث مباشرة</div>
            </div>
            <div class="dashboard-card">
              <h3>ملاحظة جديدة</h3>
              <textarea data-memory-note style="width:100%;min-height:70px;resize:vertical;">${state.note}</textarea>
              <div class="dashboard-actions" style="margin-top:8px;">
                <button data-action="save" type="button">حفظ في الذاكرة</button>
                <button data-action="ask" type="button">اسأل أمير عن الذاكرة</button>
              </div>
            </div>
            <div class="dashboard-card">
              <h3>آخر الملاحظات</h3>
              <div style="display:grid;gap:8px;margin-top:8px;">
                ${state.items.length ? state.items.map(item => `<div class="dashboard-item"><div><strong>${item}</strong></div><span>✓</span></div>`).join('') : '<div class="subtle">لا توجد ملاحظات بعد.</div>'}
              </div>
            </div>
          </section>
        `;

        container.querySelector('[data-action="save"]')?.addEventListener('click', async () => {
          const textArea = container.querySelector('[data-memory-note]');
          state.note = textArea ? textArea.value.trim() : '';
          if (!state.note) return;
          await refreshMemory();
          this.render(container);
        });

        container.querySelector('[data-action="ask"]')?.addEventListener('click', () => {
          if (window.AmeerWorkspaceShell && typeof window.AmeerWorkspaceShell.sendPrompt === 'function') {
            window.AmeerWorkspaceShell.sendPrompt('ما الذي حفظته في الذاكرة حتى الآن؟');
          }
        });
      },
      destroy(container) {
        if (container) container.innerHTML = '';
      }
    };
  }

  window.AmeerWorkspaceModules = window.AmeerWorkspaceModules || {};
  window.AmeerWorkspaceModules.memory = createMemoryModule();
})();
