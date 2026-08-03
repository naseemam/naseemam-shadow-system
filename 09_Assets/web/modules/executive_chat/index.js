(function () {
  function createExecutiveChatModule() {
    return {
      render(container) {
        if (!container) return;
        container.innerHTML = `
          <section class="module-card" style="display:grid;gap:12px;">
            <div class="dashboard-hero">
              <div>
                <div class="status-pill">Executive Chat</div>
                <h2>محادثة التنفيذ</h2>
                <p>هذه الصفحة مخصصة للتفاعل المباشر مع أمير حول التوجيه والتنفيذ.</p>
              </div>
              <div class="chip">جاهز للرد</div>
            </div>
            <div class="dashboard-card">
              <h3>ما الذي يمكن أن يفعله أمير هنا؟</h3>
              <div class="subtle">توجيه اليوم، تحليل العمل، متابعة المشاريع، وتلخيص الخطوات.</div>
            </div>
            <div class="dashboard-card">
              <h3>مثال سريع</h3>
              <div class="dashboard-actions" style="margin-top:8px;">
                <button data-action="ask" type="button">اسأل عن خطة اليوم</button>
              </div>
            </div>
          </section>
        `;

        container.querySelector('[data-action="ask"]')?.addEventListener('click', () => {
          if (window.AmeerWorkspaceShell && typeof window.AmeerWorkspaceShell.sendPrompt === 'function') {
            window.AmeerWorkspaceShell.sendPrompt('ما هي خطة اليوم التنفيذية؟');
          }
        });
      },
      destroy(container) {
        if (container) container.innerHTML = '';
      }
    };
  }

  window.AmeerWorkspaceModules = window.AmeerWorkspaceModules || {};
  window.AmeerWorkspaceModules['executive-chat'] = createExecutiveChatModule();
})();
