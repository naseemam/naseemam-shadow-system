(function () {
  function createInvestmentModule() {
    const items = [
      { name: 'الوقت', value: 'مركّز على التشغيل اليومي' },
      { name: 'الجهد', value: 'موجه نحو إكمال أدوات العمل' },
      { name: 'النتيجة', value: 'تحسين المنصة تدريجيًا' }
    ];

    return {
      render(container) {
        if (!container) return;
        container.innerHTML = `
          <section class="module-card" style="display:grid;gap:12px;">
            <div class="dashboard-hero">
              <div>
                <div class="status-pill">Investment</div>
                <h2>الاستثمار في التشغيل</h2>
                <p>تظهر هذه الصفحة كيف يُستثمر الوقت والجهد في تحسين أداة أمير.</p>
              </div>
              <div class="chip">مستثمر بوضوح</div>
            </div>
            <div class="dashboard-grid">
              ${items.map(item => `
                <div class="dashboard-card">
                  <h3>${item.name}</h3>
                  <div class="subtle">${item.value}</div>
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
  window.AmeerWorkspaceModules.investment = createInvestmentModule();
})();
