(function () {
  function createBotsModule() {
    const bots = [
      { name: 'المساعد التنفيذي', role: 'التوجيه والرد' },
      { name: 'مساعد المشاريع', role: 'تتبع الأولويات' },
      { name: 'مساعد التطوير', role: 'تنفيذ المهام البسيطة' }
    ];

    return {
      render(container) {
        if (!container) return;
        container.innerHTML = `
          <section class="module-card" style="display:grid;gap:12px;">
            <div class="dashboard-hero">
              <div>
                <div class="status-pill">Bots</div>
                <h2>الروبوتات التشغيلية</h2>
                <p>تظهر هذه الصفحة البوتات التي تدعم أمير في العمل اليومي.</p>
              </div>
              <div class="chip">3 روبوتات</div>
            </div>
            <div class="dashboard-grid">
              ${bots.map(bot => `
                <div class="dashboard-card">
                  <h3>${bot.name}</h3>
                  <div class="subtle">${bot.role}</div>
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
  window.AmeerWorkspaceModules.bots = createBotsModule();
})();
