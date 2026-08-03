(function () {
  function createDevelopmentModule() {
    const tasks = [
      { name: 'تشغيل الخادم المحلي', status: 'مكتمل' },
      { name: 'توصيل الواجهة مع /ask', status: 'مكتمل' },
      { name: 'تفعيل صفحات التشغيل', status: 'قيد التنفيذ' }
    ];

    return {
      render(container) {
        if (!container) return;
        container.innerHTML = `
          <section class="module-card" style="display:grid;gap:12px;">
            <div class="dashboard-hero">
              <div>
                <div class="status-pill">Development</div>
                <h2>لوحة التطوير</h2>
                <p>هنا يمكنك طلب من أمير قراءة المستندات أو تنفيذ أمر مرتبط بالعمل.</p>
              </div>
              <div class="chip">3 مهام</div>
            </div>
            <div class="dashboard-grid">
              ${tasks.map(task => `
                <div class="dashboard-card">
                  <h3>${task.name}</h3>
                  <div class="dashboard-item" style="margin-top:8px;">
                    <div><strong>${task.status}</strong></div>
                    <span>⚙️</span>
                  </div>
                </div>
              `).join('')}
            </div>
            <div class="dashboard-card">
              <h3>طلب تنفيذ</h3>
              <div class="subtle">يمكنك طلب من أمير البحث في المستندات أو اقتراح خطوة تنفيذية.</div>
              <div class="dashboard-actions" style="margin-top:8px;">
                <button data-action="search-docs" type="button">ابحث في المستندات</button>
                <button data-action="ask" type="button">اطلب خطة تنفيذية</button>
              </div>
            </div>
          </section>
        `;

        container.querySelector('[data-action="search-docs"]')?.addEventListener('click', async () => {
          try {
            const response = await fetch('/documents/search?q=vision');
            const payload = await response.json();
            if (window.AmeerWorkspaceShell && typeof window.AmeerWorkspaceShell.sendPrompt === 'function') {
              window.AmeerWorkspaceShell.sendPrompt(`ابحث في المستندات عن vision واذكر ما وجدت (${payload.results.length} نتيجة)`);
            }
          } catch (error) {
            console.error(error);
          }
        });

        container.querySelector('[data-action="ask"]')?.addEventListener('click', () => {
          if (window.AmeerWorkspaceShell && typeof window.AmeerWorkspaceShell.sendPrompt === 'function') {
            window.AmeerWorkspaceShell.sendPrompt('أعطني خطة تنفيذية قصيرة للمهام الحالية');
          }
        });
      },
      destroy(container) {
        if (container) container.innerHTML = '';
      }
    };
  }

  window.AmeerWorkspaceModules = window.AmeerWorkspaceModules || {};
  window.AmeerWorkspaceModules.development = createDevelopmentModule();
})();
