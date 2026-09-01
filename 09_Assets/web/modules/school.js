(() => {
  'use strict';

  const CATEGORY_LABELS = {
    student_follow_up: 'متابعة الطالبات',
    school_records: 'السجلات والقوائم',
    achievement_portfolio: 'ملف الإنجاز',
    general: 'مهام المدرسة'
  };
  const PRIORITY_LABELS = { high: 'عالية', normal: 'عادية', low: 'منخفضة' };
  const esc = value => String(value ?? '').replace(/[&<>"']/g, char => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  })[char]);

  const style = document.createElement('style');
  style.textContent = `
    #schoolDashboard{display:grid;gap:14px}.school-kpis{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px}.school-kpi{padding:15px}.school-kpi span{color:var(--muted);font-size:11px;font-weight:800}.school-kpi strong{display:block;margin-top:5px;font-size:24px}.school-layout{display:grid;grid-template-columns:minmax(0,1.5fr) minmax(280px,.7fr);gap:14px}.school-panel{padding:18px}.school-panel h3{margin:0 0 4px}.school-panel-head{display:flex;justify-content:space-between;align-items:start;gap:8px;margin-bottom:12px}.school-panel-head p{margin:4px 0 0;color:var(--muted);font-size:12px}.school-plan{display:grid;gap:9px}.school-task{display:grid;grid-template-columns:auto minmax(0,1fr) auto;align-items:start;gap:10px;padding:12px;border:1px solid var(--line);border-radius:13px;background:#fff}.school-rank{display:grid;place-items:center;width:27px;height:27px;border-radius:9px;background:var(--blueSoft);color:var(--blue);font-weight:950}.school-task h4{margin:0;font-size:13px}.school-task p{margin:4px 0 0;color:var(--muted);font-size:11px;line-height:1.6}.school-flags{display:flex;flex-wrap:wrap;gap:5px;margin-top:7px}.school-flag{display:inline-flex;padding:4px 7px;border-radius:99px;background:var(--amberSoft);color:var(--amber);font-size:10px;font-weight:850}.school-flag.category{background:var(--blueSoft);color:#315dc8}.school-done{border:1px solid #bde7cf;border-radius:9px;background:var(--greenSoft);color:var(--green);padding:7px 9px;font-size:11px;font-weight:900}.school-form{display:grid;gap:9px}.school-form input,.school-form select{width:100%;border:1px solid var(--line);border-radius:10px;background:#f8faff;padding:10px;color:var(--ink)}.school-form-row{display:grid;grid-template-columns:1fr 1fr;gap:8px}.school-alerts{display:grid;gap:8px}.school-alert{padding:10px;border-radius:11px;background:var(--amberSoft);color:#7c5407;font-size:12px;line-height:1.6}.school-next{margin:0;padding:0 20px 0 0}.school-next li{padding:6px 2px;font-size:13px;line-height:1.55}.school-error{padding:14px;border:1px solid #f0c2c5;border-radius:12px;background:#fff3f3;color:var(--red)}@media(max-width:900px){.school-kpis{grid-template-columns:repeat(2,minmax(0,1fr))}.school-layout{grid-template-columns:1fr}}@media(max-width:560px){.school-kpis,.school-form-row{grid-template-columns:1fr}.school-task{grid-template-columns:auto minmax(0,1fr)}.school-done{grid-column:2}}
  `;
  document.head.appendChild(style);

  let loading = false;

  function formatDue(task) {
    if (!task.due_at) return 'بلا موعد محدد';
    const parsed = new Date(`${String(task.due_at).slice(0, 10)}T00:00:00`);
    return Number.isNaN(parsed.getTime()) ? esc(task.due_at) : parsed.toLocaleDateString('ar-SA', { dateStyle: 'medium' });
  }

  function taskCard(task, index, numbered = true) {
    const flags = Array.isArray(task.attention_flags) ? task.attention_flags : [];
    return `
      <article class="school-task" data-school-task="${Number(task.id) || 0}">
        <span class="school-rank">${numbered ? index + 1 : '•'}</span>
        <div>
          <h4>${esc(task.title)}</h4>
          <p>${formatDue(task)} · أولوية ${esc(PRIORITY_LABELS[task.priority] || 'عادية')}</p>
          <div class="school-flags">
            <span class="school-flag category">${esc(task.category_label || CATEGORY_LABELS[task.category] || CATEGORY_LABELS.general)}</span>
            ${flags.map(flag => `<span class="school-flag">${esc(flag)}</span>`).join('')}
            ${task.missing_inputs ? `<span class="school-flag">الناقص: ${esc(task.missing_inputs)}</span>` : ''}
          </div>
        </div>
        <button class="school-done" type="button" data-complete-school-task="${Number(task.id) || 0}">تم الإنجاز</button>
      </article>`;
  }

  function render(payload) {
    const root = document.getElementById('schoolDashboard');
    if (!root) return;
    const plan = payload.weekly_plan || {};
    const tasks = Array.isArray(plan.prioritized) ? plan.prioritized : [];
    const nextThree = Array.isArray(plan.next_three) ? plan.next_three : [];
    const deadlines = Array.isArray(plan.deadlines) ? plan.deadlines : [];
    const missing = Array.isArray(plan.missing_inputs) ? plan.missing_inputs : [];
    const breakdown = payload.task_breakdown || {};
    root.innerHTML = `
      <div class="school-kpis">
        <article class="card school-kpi"><span>إجمالي المسؤوليات المفتوحة</span><strong>${Number(payload.open_tasks) || 0}</strong></article>
        <article class="card school-kpi"><span>متابعة الطالبات</span><strong>${Number(breakdown.student_follow_up) || 0}</strong></article>
        <article class="card school-kpi"><span>السجلات وملف الإنجاز</span><strong>${(Number(breakdown.school_records) || 0) + (Number(breakdown.achievement_portfolio) || 0)}</strong></article>
        <article class="card school-kpi"><span>تنبيهات هذا الأسبوع</span><strong class="${deadlines.length || missing.length ? 'warn' : 'good'}">${deadlines.length + missing.length}</strong></article>
      </div>
      <div class="school-layout">
        <article class="card school-panel">
          <div class="school-panel-head"><div><h3>خطة الأسبوع حسب الأولوية</h3><p>يرتب أمير المتأخر والقريب من موعده أولًا، ثم مستوى الأولوية.</p></div><span class="kpi">${tasks.length} بند</span></div>
          <div class="school-plan">${tasks.length ? tasks.map((task, index) => taskCard(task, index)).join('') : '<div class="empty">لا توجد مسؤوليات مسجلة بعد. أضيفي أول بند ليبني أمير الخطة الأسبوعية.</div>'}</div>
        </article>
        <div style="display:grid;gap:14px;align-content:start">
          <article class="card school-panel">
            <h3>إضافة مسؤولية</h3><p style="margin:4px 0 12px;color:var(--muted);font-size:12px">كل معلومة تدخل هنا تحفظ داخل مشروع المدرسة وتظهر في الخطة القادمة.</p>
            <form id="schoolTaskForm" class="school-form">
              <input name="title" required maxlength="180" placeholder="مثال: تحديث سجل متابعة الطالبات">
              <div class="school-form-row">
                <select name="category" aria-label="القسم"><option value="student_follow_up">متابعة الطالبات</option><option value="school_records">السجلات والقوائم</option><option value="achievement_portfolio">ملف الإنجاز</option><option value="general">مهمة مدرسية عامة</option></select>
                <select name="priority" aria-label="الأولوية"><option value="normal">أولوية عادية</option><option value="high">أولوية عالية</option><option value="low">أولوية منخفضة</option></select>
              </div>
              <input name="due_at" type="date" aria-label="الموعد النهائي">
              <input name="missing_inputs" maxlength="240" placeholder="ما المدخلات الناقصة؟ (اختياري)">
              <button class="btn primary" type="submit">إضافة إلى خطة أمير</button>
            </form>
          </article>
          <article class="card school-panel"><h3>المواعيد والنواقص</h3><div class="school-alerts" style="margin-top:10px">${
            deadlines.length || missing.length
              ? [...deadlines.map(item => `<div class="school-alert"><b>${esc(item.title)}</b><br>${esc((item.attention_flags || []).join(' · '))}</div>`), ...missing.filter(item => !deadlines.some(deadline => deadline.id === item.id)).map(item => `<div class="school-alert"><b>${esc(item.title)}</b><br>الناقص: ${esc(item.missing_inputs)}</div>`)].join('')
              : '<div class="empty">لا توجد مواعيد قريبة أو مدخلات ناقصة مسجلة.</div>'
          }</div></article>
          <article class="card school-panel"><h3>الخطوات الثلاث التالية</h3>${nextThree.length ? `<ol class="school-next">${nextThree.map(item => `<li>${esc(item.title)}</li>`).join('')}</ol>` : '<div class="empty" style="margin-top:10px">ستظهر بعد إضافة المسؤوليات.</div>'}</article>
        </div>
      </div>`;
    bindActions();
  }

  async function load() {
    const root = document.getElementById('schoolDashboard');
    if (!root || loading) return;
    loading = true;
    try {
      const response = await fetch('/school/dashboard', { cache: 'no-store' });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.reason || 'تعذر تحميل لوحة المدرسة');
      render(payload);
    } catch (error) {
      root.innerHTML = `<div class="school-error">تعذر تحميل خطة المدرسة: ${esc(error.message || 'خطأ غير معروف')}</div>`;
    } finally {
      loading = false;
    }
  }

  async function createTask(form) {
    const data = Object.fromEntries(new FormData(form).entries());
    const response = await fetch('/school/tasks', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json; charset=utf-8' },
      body: JSON.stringify(data)
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.reason || 'تعذر حفظ المسؤولية');
    form.reset();
    await load();
  }

  async function completeTask(taskId) {
    const response = await fetch(`/school/tasks/${encodeURIComponent(taskId)}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json; charset=utf-8' },
      body: JSON.stringify({ status: 'done' })
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.reason || 'تعذر تحديث المسؤولية');
    await load();
  }

  function bindActions() {
    const form = document.getElementById('schoolTaskForm');
    if (form) form.onsubmit = async event => {
      event.preventDefault();
      const button = form.querySelector('button[type="submit"]');
      button.disabled = true;
      try { await createTask(form); }
      catch (error) { window.alert(error.message || 'تعذر الحفظ'); }
      finally { button.disabled = false; }
    };
    document.querySelectorAll('[data-complete-school-task]').forEach(button => {
      button.onclick = async () => {
        button.disabled = true;
        try { await completeTask(button.dataset.completeSchoolTask); }
        catch (error) { window.alert(error.message || 'تعذر التحديث'); button.disabled = false; }
      };
    });
  }

  document.getElementById('schoolRefresh')?.addEventListener('click', load);
  document.querySelectorAll('[data-view="school"]').forEach(button => button.addEventListener('click', () => setTimeout(load, 0)));
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', load, { once: true });
  else load();
})();
