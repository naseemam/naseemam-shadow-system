(function () {
  function createWebsitesModule() {
    function getBaseUrl() {
      const { protocol, hostname, port } = window.location;
      const resolvedPort = port || (protocol === 'https:' ? '443' : '80');
      return `${protocol}//${hostname}${resolvedPort && resolvedPort !== '80' && resolvedPort !== '443' ? `:${resolvedPort}` : ''}`;
    }

    const websites = [
      { name: 'الموقع المحلي', url: `${getBaseUrl()}/`, status: 'نشط' },
      { name: 'واجهة التشغيل', url: `${getBaseUrl()}/docs`, status: 'متاحة' }
    ];

    return {
      render(container) {
        if (!container) return;
        container.innerHTML = `
          <section class="module-card" style="display:grid;gap:12px;">
            <div class="dashboard-hero">
              <div>
                <div class="status-pill">Websites</div>
                <h2>المواقع التشغيلية</h2>
                <p>هذه الصفحة تبين المواقع والروابط العامة التي يمكن الوصول إليها الآن.</p>
              </div>
              <div class="chip">2 روابط</div>
            </div>
            <div class="dashboard-grid">
              ${websites.map(site => `
                <div class="dashboard-card">
                  <h3>${site.name}</h3>
                  <div class="subtle">${site.url}</div>
                  <div class="dashboard-item" style="margin-top:8px;">
                    <div><strong>${site.status}</strong></div>
                    <span>🌐</span>
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
  window.AmeerWorkspaceModules.websites = createWebsitesModule();
})();
