(function () {
  function createProjectsModule() {
    let state = { projects: [], name: '', description: '' };

    async function refreshProjects() {
      try {
        const response = await fetch('/projects');
        const payload = await response.json();
        state.projects = Array.isArray(payload.projects) ? payload.projects : [];
      } catch (error) {
        console.error(error);
      }
    }

    async function createProject() {
      if (!state.name.trim()) return;
      const response = await fetch('/projects', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json; charset=utf-8' },
        body: JSON.stringify({ name: state.name, description: state.description })
      });
      const payload = await response.json();
      state.projects = Array.isArray(payload.projects) ? payload.projects : [];
      state.name = '';
      state.description = '';
      return payload;
    }

    return {
      render(container) {
        if (!container) return;
        container.innerHTML = `
          <section class="module-card" style="display:grid;gap:12px;">
            <div class="dashboard-hero">
              <div>
                <div class="status-pill">Projects</div>
                <h2>مشاريع التشغيل</h2>
                <p>هذه الصفحة تكتب مشروعًا حقيقيًا إلى ملف محلي وتعرضه مباشرة.</p>
              </div>
              <div class="chip">${state.projects.length} مشروع</div>
            </div>
            <div class="dashboard-card">
              <h3>إنشاء مشروع</h3>
              <input data-project-name placeholder="اسم المشروع" style="width:100%;margin-bottom:8px;" value="${state.name}" />
              <textarea data-project-description placeholder="وصف المشروع" style="width:100%;min-height:70px;resize:vertical;">${state.description}</textarea>
              <div class="dashboard-actions" style="margin-top:8px;">
                <button data-action="create" type="button">إنشاء مشروع</button>
                <button data-action="ask" type="button">اسأل أمير عن المشاريع</button>
              </div>
            </div>
            <div class="dashboard-grid">
              ${state.projects.length ? state.projects.map(project => `
                <div class="dashboard-card">
                  <h3>${project.name}</h3>
                  <div class="subtle">${project.description || 'بدون وصف'}</div>
                  <div class="dashboard-item" style="margin-top:8px;">
                    <div><strong>تمت إضافته</strong></div>
                    <span>●</span>
                  </div>
                </div>
              `).join('') : '<div class="dashboard-card"><div class="subtle">لا توجد مشاريع بعد.</div></div>'}
            </div>
          </section>
        `;

        container.querySelector('[data-action="create"]')?.addEventListener('click', async () => {
          const nameInput = container.querySelector('[data-project-name]');
          const descInput = container.querySelector('[data-project-description]');
          state.name = nameInput ? nameInput.value.trim() : '';
          state.description = descInput ? descInput.value.trim() : '';
          await createProject();
          this.render(container);
        });

        container.querySelector('[data-action="ask"]')?.addEventListener('click', () => {
          if (window.AmeerWorkspaceShell && typeof window.AmeerWorkspaceShell.sendPrompt === 'function') {
            window.AmeerWorkspaceShell.sendPrompt('ما هي المشاريع الحالية التي سجلتها؟');
          }
        });
      },
      destroy(container) {
        if (container) container.innerHTML = '';
      }
    };
  }

  window.AmeerWorkspaceModules = window.AmeerWorkspaceModules || {};
  window.AmeerWorkspaceModules.projects = createProjectsModule();
})();
