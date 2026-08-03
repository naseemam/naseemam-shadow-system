(function () {
  function createSystemModule() {
    const checks = [
      { name: 'الخادم', value: 'متصل' },
      { name: 'الـ /health', value: 'سليم' },
      { name: 'الـ /ask', value: 'يعمل' }
    ];

    return {
      render(container) {
        if (!container) return;
        container.innerHTML = `
          <section class="module-card" style="display:grid;gap:12px;">
            <div class="dashboard-hero">
              <div>
                <div class="status-pill">System</div>
                <h2>حالة النظام</h2>
                <p>هذه الصفحة تعرض الحالة التشغيلية الفورية لحالة أمير.</p>
              </div>
              <div class="chip">تشغيل مستمر</div>
            </div>
            <div class="dashboard-grid">
              ${checks.map(check => `
                <div class="dashboard-card">
                  <h3>${check.name}</h3>
                  <div class="dashboard-item" style="margin-top:8px;">
                    <div><strong>${check.value}</strong></div>
                    <span>●</span>
                  </div>
                </div>
              `).join('')}
            </div>
          </section>
        `;
      },
      destroy(container) {
        if (container) container.innerHTML = '';
      }
    };
  }

  window.AmeerWorkspaceModules = window.AmeerWorkspaceModules || {};
  window.AmeerWorkspaceModules.system = createSystemModule();
})();
