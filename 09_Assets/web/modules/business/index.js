(() => {
  const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (ch) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[ch]));
  const getJson = async (path) => { const response = await fetch(path, { headers: { Accept: 'application/json' }, cache: 'no-store' }); if (!response.ok) throw new Error(`${path}:${response.status}`); return response.json(); };
  const statusLabel = { confirmed: 'مؤكد', pending: 'قيد المراجعة', cancelled: 'ملغى', unavailable: 'غير متاح', conflict: 'متعارض' };
  const statusClass = (status) => ({ confirmed: 'good', pending: 'warn', cancelled: 'muted', unavailable: 'bad', conflict: 'bad' }[status] || 'muted');
  const bookingRows = (items) => {
    if (!items || !items.length) return '<div class="dashboard-item"><span>لا توجد حجوزات مسجلة حاليًا</span><span class="chip muted">فارغ</span></div>';
    return items.map((item) => `<div class="dashboard-item"><div><strong>${esc(item.title || 'حجز')}</strong><small style="display:block;opacity:.7">${esc(item.starts_at || 'موعد غير محدد')} · ${esc(item.employee_name || item.employee_id || 'غير مسند')}</small></div><span class="chip ${statusClass(item.status)}">${esc(statusLabel[item.status] || item.status || 'غير معروف')}</span></div>`).join('');
  };
  const rows = (items, empty) => !items?.length ? `<div class="dashboard-item"><span>${empty}</span></div>` : items.map((item) => `<div class="dashboard-item"><div><strong>${esc(item.name || item.title || item.sku || '—')}</strong><small style="display:block;opacity:.7">${esc(item.role || item.phone || item.starts_at || (item.stock ?? ''))}</small></div><span>#${esc(item.id)}</span></div>`).join('');
  const countStatuses = (items) => (items || []).reduce((acc, item) => { const key = item.status || 'unknown'; acc[key] = (acc[key] || 0) + 1; return acc; }, {});

  function createBusinessModule() {
    return {
      async render(container) {
        if (!container) return;
        const load = async () => {
          container.innerHTML = '<section class="module-card"><div class="dashboard-hero"><div><div class="status-pill">مركز حلم الندى</div><h2>لوحة المراقبة</h2><p>جاري قراءة الحجوزات وصلاحيات أمير...</p></div><div class="chip">جاري التحميل</div></div></section>';
          try {
            const [profile, dashboard, employees, customers, inventory, bookings, authority] = await Promise.all([
              getJson('/center/profile'), getJson('/center/dashboard'), getJson('/center/employees'), getJson('/center/customers'), getJson('/center/inventory'), getJson('/center/bookings'), getJson('/agent/authority')
            ]);
            const summary = dashboard.dashboard || {};
            const list = bookings.bookings || [];
            const counts = countStatuses(list);
            const workerCount = authority.workers?.length ?? authority.authority?.workers?.length ?? '—';
            const finalOwner = authority.final_approval_owner || authority.authority?.final_approval_owner || 'founder';
            container.innerHTML = `
              <section class="module-card" style="display:grid;gap:14px;">
                <div class="dashboard-hero"><div><div class="status-pill">${esc(profile.center?.name || 'مركز حلم الندى')}</div><h2>لوحة الحجوزات والصلاحيات</h2><p>مراقبة التشغيل وقرارات أمير من مصدر قراءة موثوق.</p></div><div style="display:flex;gap:8px;align-items:center"><span class="chip good">متصل</span><button type="button" class="secondary" data-dashboard-refresh>تحديث</button></div></div>
                <div style="display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px">
                  <div class="dashboard-card"><small>كل الحجوزات</small><strong class="metric">${esc(list.length)}</strong></div>
                  <div class="dashboard-card"><small>مؤكدة</small><strong class="metric good">${esc(counts.confirmed || summary.confirmed_bookings || 0)}</strong></div>
                  <div class="dashboard-card"><small>قيد المراجعة</small><strong class="metric warn">${esc(counts.pending || 0)}</strong></div>
                  <div class="dashboard-card"><small>تعارض/غير متاح</small><strong class="metric bad">${esc((counts.conflict || 0) + (counts.unavailable || 0))}</strong></div>
                </div>
                <div class="dashboard-card"><div class="section-title"><h3>صلاحيات أمير</h3><span class="chip good">Orchestrator مركزي</span></div><div class="dashboard-item"><span>تأكيد الحجز العادي المتاح</span><strong class="good">مسموح</strong></div><div class="dashboard-item"><span>التعامل مع التعارض</span><strong class="warn">يُرفض ويُسجل</strong></div><div class="dashboard-item"><span>الدفع أو الاستثناءات الحساسة</span><strong class="warn">موافقة ${esc(finalOwner)}</strong></div><div class="dashboard-item"><span>عدد العمال تحت الإدارة</span><strong>${esc(workerCount)}</strong></div></div>
                <div class="dashboard-card"><div class="section-title"><h3>حالة الحجوزات</h3><span>آخر قراءة مباشرة</span></div>${bookingRows(list)}</div>
                <div style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px"><div class="dashboard-card"><h3>الموظفون</h3>${rows(employees.employees, 'لا توجد سجلات موظفين')}</div><div class="dashboard-card"><h3>العملاء</h3>${rows(customers.customers, 'لا توجد سجلات عملاء')}</div><div class="dashboard-card"><h3>المخزون</h3>${rows(inventory.items, 'لا توجد منتجات')}</div></div>
              </section>`;
            container.querySelector('[data-dashboard-refresh]')?.addEventListener('click', load);
          } catch (error) {
            container.innerHTML = `<section class="module-card"><div class="dashboard-hero"><div><div class="status-pill">مركز حلم الندى</div><h2>تعذر تحميل اللوحة</h2><p>تحقق من اتصال الخادم ثم أعد المحاولة.</p></div><div class="chip bad">خطأ</div></div><div class="dashboard-card">${esc(error.message)}</div></section>`;
          }
        };
        await load();
      },
      destroy(container) { if (container) container.innerHTML = ''; }
    };
  }
  window.AmeerWorkspaceModules = window.AmeerWorkspaceModules || {};
  window.AmeerWorkspaceModules.business = createBusinessModule();
})();
