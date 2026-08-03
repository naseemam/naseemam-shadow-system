(function () {
  function applyTheme(theme) {
    const resolved = theme === 'dark' ? 'dark' : 'light';
    document.documentElement.setAttribute('data-theme', resolved);
    localStorage.setItem('ameer-theme', resolved);
    const btn = document.getElementById('themeToggleBtn');
    if (btn) {
      btn.textContent = resolved === 'dark' ? '☀️ Light' : '🌗 Theme';
    }
  }

  function bindThemeButton() {
    const btn = document.getElementById('themeToggleBtn');
    if (!btn) return;
    btn.addEventListener('click', () => {
      const next = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
      applyTheme(next);
    });
  }

  function init() {
    const storedTheme = localStorage.getItem('ameer-theme') || 'light';
    applyTheme(storedTheme);
    bindThemeButton();
  }

  window.AmeerTheme = { init, applyTheme };
})();
