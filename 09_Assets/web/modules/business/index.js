(function () {
  const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (ch) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[ch]));

  async function getJson(path) {
    const response = await fetch(path, { headers: { Accept: 'application/json' } });
    if (!response.ok) throw new Error(`${path}:${response.status}`);
    return response.json();
  }

  function rows(items, empty) {
    if (!items || !items.length) return `<div class="dashboard-item"><span>${empty}</span></div>`;
    return items.map((item) => `<div class="dashboard-item"><div><strong>${esc(item.name || item.title || item.sku || '—')}</strong><small style="display:block;opacity:.7">${esc(item.role || item.phone || item.starts_at || item.stock ?? '')}</small></div><span>#${esc(item.id)}</span></div>`).join('');
  }

  function createBusinessModule() {
    return {
      async render(container) {
        if (!container) return;
        container.innerHTML = `<section class="module-card"><div class="dashboard-hero"><div><div class="status-pill">مركز حلم الندى</div><h2>لوحة الإدارة</h2><p>المخزون والموظفون والعملاء والحجوزات.</p></div><div class="chip">جاري التحميل</div></div><div class="dashboard-card">جارٍ جلب بيانات المركز...</div></section>`;
        try {
          const [profile, dashboard, employees, customers, inventory, bookings] = await Promise.all([
            getJson('/center/profile'), getJson('/center/dashboard'), getJson('/center/employees'),
            getJson('/center/customers'), getJson('/center/inventory'), getJson('/center/bookings')
          ]);
          const summary = dashboard.dashboard || {};
          container.innerHTML = `
            <section class="module-card" style="display:grid;gap:12px;">
              <div class="dashboard-hero"><div><div class="status-pill">${esc(profile.center?.name)}</div><h2>لوحة الإدارة</h2><p>المنطقة الزمنية: ${esc(profile.center?.timezone)} · العملة: ${esc(profile.center?.currency)}</p></div><div class="chip">متصل</div></div>
              <div class="dashboard-card"><h3>ملخص التشغيل</h3><div class="dashboard-item"><span>المنتجات</span><strong>${esc(summary.products)}</strong></div><div class="dashboard-item"><span>الموظفون</span><strong>${esc(summary.employees)}</strong></div><div class="dashboard-item"><span>الحجوزات المؤكدة</span><strong>${esc(summary.confirmed_bookings)}</strong></div><div class="dashboard-item"><span>الطلبات المفتوحة</span><strong>${esc(summary.open_orders)}</strong></div></div>
              <div style="display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;">
                <div class="dashboard-card"><h3>الموظفون</h3>${rows(employees.employees, 'لا توجد سجلات موظفين')}</div>
                <div class="dashboard-card"><h3>العملاء</h3>${rows(customers.customers, 'لا توجد سجلات عملاء')}</div>
                <div class="dashboard-card"><h3>المخزون</h3>${rows(inventory.items, 'لا توجد منتجات')}</div>
                <div class="dashboard-card"><h3>الحجوزات</h3>${rows(bookings.bookings, 'لا توجد حجوزات')}</div>
              </div>
            </section>`;
        } catch (error) {
          container.innerHTML = `<section class="module-card"><div class="dashboard-hero"><div><div class="status-pill">مركز حلم الندى</div><h2>تعذر تحميل البيانات</h2><p>تحقق من اتصال الخادم ثم أعد فتح القسم.</p></div><div class="chip">خطأ</div></div><div class="dashboard-card">${esc(error.message)}</div></section>`;
        }
      },
      destroy(container) { if (container) container.innerHTML = ''; }
    };
  }

  window.AmeerWorkspaceModules = window.AmeerWorkspaceModules || {};
  window.AmeerWorkspaceModules.business = createBusinessModule();
})();
