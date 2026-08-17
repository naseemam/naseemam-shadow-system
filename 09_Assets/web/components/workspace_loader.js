(function () {
  const moduleDefinitions = [
    { key: 'home', label: 'Home', hostId: 'homeContent', component: 'home' },
    { key: 'executive_chat', label: 'Executive Chat', hostId: 'executiveChatContent', component: 'executive_chat' },
    { key: 'friendly_chat', label: 'Friendly Chat', hostId: 'friendlyChatContent', component: 'friendly_chat' },
    { key: 'projects', label: 'Projects', hostId: 'projectsContent', component: 'projects' },
    { key: 'memory', label: 'Memory', hostId: 'memoryContent', component: 'memory' },
    { key: 'development', label: 'Development', hostId: 'developmentContent', component: 'development' },
    { key: 'websites', label: 'Websites', hostId: 'websitesContent', component: 'websites' },
    { key: 'business', label: 'Business', hostId: 'businessContent', component: 'business' },
    { key: 'investment', label: 'Investment', hostId: 'investmentContent', component: 'investment' },
    { key: 'bots', label: 'Bots', hostId: 'botsContent', component: 'bots' },
    { key: 'system', label: 'System', hostId: 'systemContent', component: 'system' }
  ];

  const registry = {};
  let activeKey = null;
  let activeHost = null;

  function escapeHtml(text) {
    return String(text || '')
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
      .replaceAll("'", '&#039;');
  }

  function placeholderModule(title, message) {
    return {
      render(container) {
        if (!container) return;
        container.innerHTML = `
          <section class="module-card">
            <div class="status-pill">Placeholder</div>
            <h2>${escapeHtml(title)}</h2>
            <p>${escapeHtml(message)}</p>
          </section>
        `;
      },
      destroy(container) {
        if (container) {
          container.innerHTML = '';
        }
      }
    };
  }

  function getHostForKey(key) {
    const definition = moduleDefinitions.find(item => item.key === key);
    if (!definition) return null;
    let host = document.getElementById(definition.hostId);
    if (!host && definition.key === 'friendly_chat') {
      const content = document.querySelector('.content') || document.body;
      host = document.createElement('div');
      host.id = definition.hostId;
      host.className = 'page-view';
      content.appendChild(host);
    }
    return host;
  }

  function createHomeModule() {
    return {
      render(container) {
        if (!container) return;
        container.innerHTML = `
          <section class="module-card">
            <div class="dashboard-hero">
              <div>
                <div class="status-pill">Home Module</div>
                <h2>لوحة القيادة المنزلية</h2>
                <p>المكوّن الرئيسي للمساحة الحالية يتم تحميله عبر Workspace Loader.</p>
              </div>
            </div>
            <div class="dashboard-grid" style="margin-top:12px;">
              <div class="dashboard-card">
                <h3>Founder Overview</h3>
                <div class="subtle">نظرة عامة على أولويات العمل والوضوح اليومي.</div>
              </div>
              <div class="dashboard-card">
                <h3>Priority Focus</h3>
                <div class="subtle">التركيز على الخطوات القادمة التي تحتاج متابعة.</div>
              </div>
            </div>
          </section>
        `;
      },
      destroy(container) {
        if (container) {
          container.innerHTML = '';
        }
      }
    };
  }

  function registerAllModules() {
    moduleDefinitions.forEach(definition => {
      const existingComponent = window.AmeerComponents && window.AmeerComponents[definition.component];
      if (definition.key === 'home') {
        registry[definition.key] = createHomeModule();
        return;
      }
      if (existingComponent && typeof existingComponent.render === 'function') {
        registry[definition.key] = {
          render(container) {
            existingComponent.render(container);
          },
          destroy(container) {
            if (container) container.innerHTML = '';
          }
        };
        return;
      }
      registry[definition.key] = placeholderModule(definition.label, 'Module scaffold ready for future content.');
    });
  }

  function unloadActiveModule() {
    if (activeHost && activeKey && registry[activeKey] && typeof registry[activeKey].destroy === 'function') {
      registry[activeKey].destroy(activeHost);
    }
    activeKey = null;
    activeHost = null;
  }

  function loadModule(key) {
    if (!key) {
      key = 'home';
    }
    const module = registry[key];
    const host = getHostForKey(key);

    if (!module || !host) {
      return null;
    }

    if (activeKey === key && activeHost === host) {
      return module;
    }

    if (activeHost && activeKey && activeKey !== key && registry[activeKey] && typeof registry[activeKey].destroy === 'function') {
      registry[activeKey].destroy(activeHost);
    }

    host.innerHTML = '';
    module.render(host);
    activeKey = key;
    activeHost = host;
    return module;
  }

  registerAllModules();

  window.AmeerWorkspaceLoader = {
    load: loadModule,
    unload: unloadActiveModule,
    getActiveKey: function () {
      return activeKey;
    },
    getRegisteredModules: function () {
      return moduleDefinitions.map(item => item.key);
    }
  };
})();
