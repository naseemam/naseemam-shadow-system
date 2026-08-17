(function () {
  const registry = window.AmeerWorkspaceModules || (window.AmeerWorkspaceModules = {});
  const modulePaths = {
    home: './modules/home/index.js',
    'executive-chat': './modules/executive_chat/index.js',
    'friendly-chat': './modules/friendly_chat/index.js',
    executive_chat: './modules/executive_chat/index.js',
    projects: './modules/projects/index.js',
    memory: './modules/memory/index.js',
    development: './modules/development/index.js',
    websites: './modules/websites/index.js',
    business: './modules/business/index.js',
    investment: './modules/investment/index.js',
    bots: './modules/bots/index.js',
    system: './modules/system/index.js',
    pricing: './modules/pricing/index.js',
    services: './modules/services/index.js',
    about: './modules/about/index.js',
    contact: './modules/contact/index.js',
  };

  const hostIds = {
    home: 'homeContent',
    'executive-chat': 'executiveChatContent',
    'friendly-chat': 'friendlyChatContent',
    executive_chat: 'executiveChatContent',
    projects: 'projectsContent',
    memory: 'memoryContent',
    development: 'developmentContent',
    websites: 'websitesContent',
    business: 'businessContent',
    investment: 'investmentContent',
    bots: 'botsContent',
    system: 'systemContent',
    pricing: 'pricingContent',
    services: 'servicesContent',
    about: 'aboutContent',
    contact: 'contactContent',
  };

  let activeKey = null;
  let activeHost = null;
  const loadedKeys = new Set();

  function placeholderModule(title, message) {
    return {
      render(container) {
        if (!container) return;
        container.innerHTML = `
          <section class="module-card">
            <div class="status-pill">Placeholder</div>
            <h2>${title}</h2>
            <p>${message}</p>
          </section>
        `;
      },
      destroy(container) {
        if (container) container.innerHTML = '';
      }
    };
  }

  function getHostForKey(key) {
    const resolvedKey = key === 'executive_chat' ? 'executive-chat' : key;
    return hostIds[resolvedKey] ? document.getElementById(hostIds[resolvedKey]) : null;
  }

  function ensureModuleLoaded(key) {
    return new Promise((resolve) => {
      const normalizedKey = key === 'executive_chat' ? 'executive-chat' : key;
      if (registry[normalizedKey] || loadedKeys.has(normalizedKey)) {
        resolve();
        return;
      }
      const script = document.createElement('script');
      script.src = modulePaths[normalizedKey];
      script.onload = () => {
        loadedKeys.add(normalizedKey);
        resolve();
      };
      script.onerror = () => resolve();
      document.head.appendChild(script);
    });
  }

  async function load(key) {
    const moduleKey = key || 'home';
    const normalizedKey = moduleKey === 'executive_chat' ? 'executive-chat' : moduleKey;
    await ensureModuleLoaded(normalizedKey);
    const module = registry[normalizedKey] || placeholderModule(normalizedKey, 'Module scaffold ready for future content.');
    const host = getHostForKey(moduleKey);

    if (!host) return null;
    if (activeKey === moduleKey && activeHost === host) return module;

    if (activeHost && activeKey && activeKey !== moduleKey && registry[activeKey] && typeof registry[activeKey].destroy === 'function') {
      registry[activeKey].destroy(activeHost);
    }

    host.innerHTML = '';
    module.render(host);
    activeKey = moduleKey;
    activeHost = host;
    return module;
  }

  window.AmeerWorkspaceLoader = {
    load,
    unload: function () {
      if (activeHost && activeKey && registry[activeKey] && typeof registry[activeKey].destroy === 'function') {
        registry[activeKey].destroy(activeHost);
      }
      activeKey = null;
      activeHost = null;
    },
    getActiveKey: function () {
      return activeKey;
    }
  };
})();
