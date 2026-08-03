(function () {
  const dashboardData = {
    priorities: [
      { title: 'إكمال خطة الأسبوع', meta: 'التركيز على أولويات العمل' },
      { title: 'مراجعة الملاحظات المهمة', meta: 'تنظيم الذاكرة والمشاريع' }
    ],
    projects: [
      { title: 'Ameer Workspace', meta: 'الواجهة الأساسية' },
      { title: 'حلم الندى', meta: 'خطة التطوير' }
    ],
    tasks: [
      { title: 'تحديث الواجهة', meta: 'Dashboard + Sidebar' },
      { title: 'تنظيم المعرفة', meta: 'الذاكرة والمشاريع' }
    ],
    health: [
      { title: 'الخادم', meta: 'متصل' },
      { title: 'البيانات', meta: 'محدثة محليًا' }
    ],
    decisions: [
      { title: 'التركيز على Dashboard', meta: 'تمت الموافقة' },
      { title: 'العمل على الواجهة فقط', meta: 'بدون Core أو Server' }
    ],
    approvals: [
      { title: 'إقرار الخطوة الحالية', meta: 'بانتظار التحقق' },
      { title: 'توسيع لوحة القيادة', meta: 'مفتوح لاحقًا' }
    ],
    actions: [
      { title: 'فتح محادثة جديدة', meta: 'ابدأ من هنا' },
      { title: 'استعراض الوثائق', meta: 'اعرض الملفات المحلية' }
    ]
  };

  function escapeHtml(text) {
    return String(text || '')
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
      .replaceAll("'", '&#039;');
  }

  function renderDashboard(host) {
    if (!host) return;
    host.innerHTML = `
      <div class="dashboard-hero">
        <div>
          <div class="status-pill">Home Dashboard</div>
          <h2>لوحة القيادة المنزلية</h2>
          <p>مكوّن مستقل للعرض السريع والهيكل الحالي.</p>
        </div>
        <div class="dashboard-actions">
          <button>+ نشاط جديد</button>
          <button style="background: var(--panel-soft); color: var(--ink); border: 1px solid var(--line);">عرض التفاصيل</button>
        </div>
      </div>
      <div class="dashboard-grid" style="margin-top:12px;">
        <div class="dashboard-card">
          <h3>Founder Overview</h3>
          <div class="subtle">Ameer Workspace is structured around a clear operating shell for focus, momentum, and local execution.</div>
        </div>
        <div class="dashboard-card">
          <h3>Today's Priorities</h3>
          <div class="subtle">الأولويات الحالية التي تحتاج متابعة فورية.</div>
          ${dashboardData.priorities.map(item => `<div class="dashboard-item"><div><strong>${escapeHtml(item.title)}</strong><div class="subtle">${escapeHtml(item.meta)}</div></div><span>↗</span></div>`).join('')}
        </div>
        <div class="dashboard-card">
          <h3>Active Projects</h3>
          <div class="subtle">المشاريع النشطة حاليًا.</div>
          ${dashboardData.projects.map(item => `<div class="dashboard-item"><div><strong>${escapeHtml(item.title)}</strong><div class="subtle">${escapeHtml(item.meta)}</div></div><span>●</span></div>`).join('')}
        </div>
        <div class="dashboard-card">
          <h3>Active Tasks</h3>
          <div class="subtle">المهام المفتوحة الحالية.</div>
          ${dashboardData.tasks.map(item => `<div class="dashboard-item"><div><strong>${escapeHtml(item.title)}</strong><div class="subtle">${escapeHtml(item.meta)}</div></div><span>✓</span></div>`).join('')}
        </div>
        <div class="dashboard-card">
          <h3>Recent Decisions</h3>
          <div class="subtle">القرارات الأخيرة التي شكلت التوجه.</div>
          ${dashboardData.decisions.map(item => `<div class="dashboard-item"><div><strong>${escapeHtml(item.title)}</strong><div class="subtle">${escapeHtml(item.meta)}</div></div><span>⤴</span></div>`).join('')}
        </div>
        <div class="dashboard-card">
          <h3>Pending Approvals</h3>
          <div class="subtle">الموافقة المطلوبة على الخطوات القادمة.</div>
          ${dashboardData.approvals.map(item => `<div class="dashboard-item"><div><strong>${escapeHtml(item.title)}</strong><div class="subtle">${escapeHtml(item.meta)}</div></div><span>!</span></div>`).join('')}
        </div>
        <div class="dashboard-card">
          <h3>System Health</h3>
          <div class="subtle">حالة النظام والبيئة.</div>
          ${dashboardData.health.map(item => `<div class="dashboard-item"><div><strong>${escapeHtml(item.title)}</strong><div class="subtle">${escapeHtml(item.meta)}</div></div><span>●</span></div>`).join('')}
        </div>
        <div class="dashboard-card" style="grid-column: 1 / -1;">
          <h3>Quick Actions</h3>
          <div class="subtle">إجراءات سريعة للانتقال إلى العمل.</div>
          ${dashboardData.actions.map(item => `<div class="dashboard-item"><div><strong>${escapeHtml(item.title)}</strong><div class="subtle">${escapeHtml(item.meta)}</div></div><span>→</span></div>`).join('')}
        </div>
      </div>
    `;
  }

  window.AmeerWorkspaceComponents = window.AmeerWorkspaceComponents || {};
  window.AmeerWorkspaceComponents.renderDashboard = function (host) {
    renderDashboard(host);
  };
})();
