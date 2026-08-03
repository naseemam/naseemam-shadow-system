(function () {
  function createHomeModule() {
    const state = {
      focusMode: 'daily',
      completed: 2,
      insight: 'تسجيل أول خطوة واضحة اليوم',
      priorities: [
        'إغلاق النقطة الأكثر أهمية اليوم',
        'مراجعة التقدم على المشاريع المفتوحة',
        'تحديث التوجيه قبل نهاية العمل'
      ]
    };

    function renderSummaryText() {
      const focusLabels = {
        daily: 'التركيز اليومي',
        weekly: 'التركيز الأسبوعي',
        quarterly: 'التركيز الربعي'
      };
      return `${focusLabels[state.focusMode]} • ${state.completed}/4 خطوات مكتملة`;
    }

    function render(container, module) {
      if (!container) return;
      container.innerHTML = `
        <section class="module-card" style="display:grid;gap:12px;">
          <div class="dashboard-hero">
            <div>
              <div class="status-pill">Home Module</div>
              <h2>لوحة القيادة المنزلية</h2>
              <p>المنصة الآن تعكس الحالة الحالية وتسمح بالتفاعل مباشرة من داخل الوحدة.</p>
            </div>
            <div class="chip">${renderSummaryText()}</div>
          </div>

          <div class="dashboard-grid">
            <div class="dashboard-card">
              <h3>التركيز الحالي</h3>
              <div class="subtle">اختر منظور العمل الذي تريد مراجعته الآن.</div>
              <div class="dashboard-actions" style="margin-top:8px;">
                <button data-action="focus" data-mode="daily">يومي</button>
                <button data-action="focus" data-mode="weekly" style="background:var(--panel-soft);color:var(--ink);border:1px solid var(--line);">أسبوعي</button>
                <button data-action="focus" data-mode="quarterly" style="background:var(--panel-soft);color:var(--ink);border:1px solid var(--line);">ربعي</button>
              </div>
            </div>

            <div class="dashboard-card">
              <h3>أولويات اليوم</h3>
              <div class="subtle">قائمة أولويات قابلة للتحديث مباشرة.</div>
              <div style="display:grid;gap:8px;margin-top:8px;">
                ${state.priorities.map((item) => `<div class="dashboard-item"><div><strong>${item}</strong></div><span>✓</span></div>`).join('')}
              </div>
            </div>

            <div class="dashboard-card">
              <h3>التقدم</h3>
              <div class="subtle">انقر لإضافة خطوة مكتملة ومراجعة التقدم.</div>
              <div class="dashboard-item" style="margin-top:8px;"><div><strong>${state.completed}/4 خطوات مكتملة</strong><div class="subtle">${state.insight}</div></div><span>↗</span></div>
              <div class="dashboard-actions" style="margin-top:8px;">
                <button data-action="complete">تسجيل تقدم</button>
                <button data-action="next-insight" style="background:var(--panel-soft);color:var(--ink);border:1px solid var(--line);">Insight جديد</button>
                <button data-action="ask-home" style="background:var(--accent-2);color:white;">اسأل أمير</button>
              </div>
            </div>

            <div class="dashboard-card">
              <h3>الملخص التنفيذي</h3>
              <div class="subtle">هذا العرض يبين أن الوحدة مستقلة وتدير حالتها الخاصة.</div>
              <div class="dashboard-item" style="margin-top:8px;"><div><strong>الحالة الحالية</strong><div class="subtle">${renderSummaryText()}</div></div><span>●</span></div>
            </div>
          </div>
        </section>
      `;

      container.querySelectorAll('[data-action]').forEach((button) => {
        button.addEventListener('click', () => {
          const action = button.getAttribute('data-action');
          if (action === 'focus') {
            state.focusMode = button.getAttribute('data-mode') || 'daily';
          } else if (action === 'complete') {
            state.completed = Math.min(4, state.completed + 1);
            state.insight = 'تمت إضافة خطوة جديدة إلى التقدم';
          } else if (action === 'next-insight') {
            const nextInsights = [
              'تمت مراجعة أولويات العمل بصوت واضح',
              'تم تحديد ما يحتاج إلى متابعة فورية',
              'تمت إضافة نقطة جديدة إلى الخطة اليومية'
            ];
            state.insight = nextInsights[state.completed % nextInsights.length];
          } else if (action === 'ask-home') {
            if (window.AmeerWorkspaceShell && typeof window.AmeerWorkspaceShell.sendPrompt === 'function') {
              window.AmeerWorkspaceShell.sendPrompt('أعطني ملخصًا سريعًا عن الوضع الحالي');
            }
          }
          render(container, module);
        });
      });
    }

    return {
      state,
      render(container) {
        render(container, this);
      },
      destroy(container) {
        if (container) container.innerHTML = '';
      }
    };
  }

  window.AmeerWorkspaceModules = window.AmeerWorkspaceModules || {};
  window.AmeerWorkspaceModules.home = createHomeModule();
})();
