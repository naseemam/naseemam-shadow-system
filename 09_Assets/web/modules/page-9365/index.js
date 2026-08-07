(function () {
  function createPage9365Module() {
    return {
      render(container) {
        if (!container) return;
        container.innerHTML = `
          <section class="module-card" style="display:grid;gap:12px;">
            <div class="dashboard-hero">
              <div>
                <div class="status-pill">Generated Page</div>
                <h2>عن حلم الندى</h2>
                <p>حلم الندى</p>
              </div>
              <div class="chip">عن حلم الندى</div>
            </div>
            <div class="dashboard-card">
              <h3>تم إنشاؤها عبر التنفيذ</h3>
              <div class="subtle">هذه الصفحة أضيفت تلقائيًا إلى الواجهة والتنقل.</div>
              <div class="dashboard-actions" style="margin-top:8px;">
                <button data-action="ask-page" type="button">اسأل أمير عن هذه الصفحة</button>
                <button data-action="improve-page" type="button" style="background:var(--accent-2);color:white;">نفّذ تحسينًا أوليًا</button>
                <button data-action="open-chat" type="button" style="background:var(--panel-soft);color:var(--ink);border:1px solid var(--line);">افتح المحادثة التنفيذية</button>
              </div>
            </div>
          </section>
        `;
        container.querySelector('[data-action="ask-page"]')?.addEventListener('click', () => {
          if (window.AmeerWorkspaceShell && typeof window.AmeerWorkspaceShell.sendPrompt === 'function') {
            window.AmeerWorkspaceShell.sendPrompt("أعطني ملخصًا سريعًا عن صفحة عن حلم الندى وما الذي تفعله الآن.");
          }
        });
        container.querySelector('[data-action="improve-page"]')?.addEventListener('click', () => {
          if (window.AmeerWorkspaceShell && typeof window.AmeerWorkspaceShell.sendPrompt === 'function') {
            window.AmeerWorkspaceShell.sendPrompt("اقترح تحسينات عملية لصفحة عن حلم الندى ثم ابدأ بتنفيذ أول تحسين آمن داخل الواجهة.");
          }
        });
        container.querySelector('[data-action="open-chat"]')?.addEventListener('click', () => {
          if (window.AmeerWorkspaceShell && typeof window.AmeerWorkspaceShell.openPage === 'function') {
            window.AmeerWorkspaceShell.openPage('executive-chat');
          }
        });
      },
      destroy(container) {
        if (container) container.innerHTML = '';
      }
    };
  }

  window.AmeerWorkspaceModules = window.AmeerWorkspaceModules || {};
  window.AmeerWorkspaceModules['page-9365'] = createPage9365Module();
})();
