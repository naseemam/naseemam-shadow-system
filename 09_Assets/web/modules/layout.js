(function () {
  const navItems = [
    { key: 'home', label: 'Home', icon: '🏠' },
    { key: 'executive-chat', label: 'Executive Chat', icon: '💬' },
    { key: 'friendly_chat', label: 'Friendly Chat', icon: '☕' },
    { key: 'projects', label: 'Projects', icon: '📁' },
    { key: 'memory', label: 'Memory', icon: '🧠' },
    { key: 'development', label: 'Development', icon: '🛠' },
    { key: 'websites', label: 'Websites', icon: '🌐' },
    { key: 'business', label: 'Business', icon: '💼' },
    { key: 'investment', label: 'Investment', icon: '📈' },
    { key: 'bots', label: 'Bots', icon: '🤖' },
    { key: 'system', label: 'System', icon: '⚙️' }
  ];

  let activePage = 'home';

  function renderNavigation() {
    const host = document.getElementById('pageTabs');
    if (!host) return;
    host.innerHTML = navItems.map(item => `
      <button class="tab ${activePage === item.key ? 'active' : ''}" data-page="${item.key}" type="button">${item.icon} ${item.label}</button>
    `).join('');
  }

  function setActivePage(pageKey) {
    activePage = pageKey || 'home';
    document.querySelectorAll('.page-view').forEach(view => {
      const key = view.id.replace('view-', '');
      view.classList.toggle('active', activePage === key);
    });
    renderNavigation();
  }

  function init() {
    renderNavigation();
    setActivePage(activePage);
    document.querySelectorAll('#pageTabs .tab').forEach(btn => {
      btn.addEventListener('click', () => {
        if (window.AmeerRouter && typeof window.AmeerRouter.navigate === 'function') {
          window.AmeerRouter.navigate(btn.getAttribute('data-page'));
        }
      });
    });
  }

  window.AmeerLayout = {
    init,
    setActivePage,
    getState: function () {
      return { activePage };
    },
    navItems
  };
})();
