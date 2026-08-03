(function () {
  const routeMap = {
    home: 'home',
    'executive-chat': 'executive-chat',
    projects: 'projects',
    memory: 'memory',
    development: 'development',
    websites: 'websites',
    business: 'business',
    investment: 'investment',
    bots: 'bots',
    system: 'system'
  };

  let currentRoute = 'home';

  function normalizeRoute(pageKey) {
    return routeMap[pageKey] || 'home';
  }

  function navigate(pageKey) {
    const resolvedKey = pageKey || 'home';
    currentRoute = resolvedKey;
    const moduleKey = normalizeRoute(resolvedKey);
    if (window.AmeerLayout && typeof window.AmeerLayout.setActivePage === 'function') {
      window.AmeerLayout.setActivePage(resolvedKey);
    }
    if (window.AmeerWorkspaceLoader && typeof window.AmeerWorkspaceLoader.load === 'function') {
      window.AmeerWorkspaceLoader.load(moduleKey);
    }
    window.dispatchEvent(new CustomEvent('ameer:navigate', { detail: { page: resolvedKey, module: moduleKey } }));
  }

  function init() {
    navigate(currentRoute);
  }

  window.AmeerRouter = {
    init,
    navigate,
    getCurrent: function () {
      return currentRoute;
    }
  };
})();
