(function () {
  function init() {
    if (window.AmeerLayout && typeof window.AmeerLayout.init === 'function') {
      window.AmeerLayout.init();
    }
    if (window.AmeerTheme && typeof window.AmeerTheme.init === 'function') {
      window.AmeerTheme.init();
    }
    if (window.AmeerRouter && typeof window.AmeerRouter.init === 'function') {
      window.AmeerRouter.init();
    }
    if (window.AmeerWorkspaceLoader && typeof window.AmeerWorkspaceLoader.load === 'function') {
      window.AmeerWorkspaceLoader.load('home');
    }
    if (window.AmeerWorkspaceShell && typeof window.AmeerWorkspaceShell.init === 'function') {
      window.AmeerWorkspaceShell.init();
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  window.AmeerApp = { init };
})();
