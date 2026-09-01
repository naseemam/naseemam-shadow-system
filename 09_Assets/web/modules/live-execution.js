(() => {
  'use strict';

  const nativeFetch = window.fetch.bind(window);
  const cards = new Map();
  const timers = new Map();
  const terminal = new Set(['completed', 'blocked', 'failed']);
  const esc = value => String(value ?? '').replace(/[&<>"']/g, char => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  })[char]);

  const style = document.createElement('style');
  style.textContent = `
    .live-execution{align-self:stretch;max-width:100%;border:1px solid #cfdbf6;border-radius:17px;background:linear-gradient(145deg,#f8faff,#fff);overflow:hidden;box-shadow:0 8px 22px rgba(36,69,139,.07);direction:rtl}.live-execution-head{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:12px 14px;border-bottom:1px solid #e1e8f6;background:#f4f7ff}.live-execution-title{display:flex;align-items:center;gap:8px;font-size:13px;font-weight:950;color:#244d9f}.live-execution-pulse{width:9px;height:9px;border-radius:50%;background:#3b6fe8;box-shadow:0 0 0 0 rgba(59,111,232,.38);animation:livePulse 1.35s infinite}.live-execution.completed .live-execution-pulse{background:#12845a;animation:none}.live-execution.blocked .live-execution-pulse,.live-execution.failed .live-execution-pulse{background:#bd3640;animation:none}.live-execution-state{font-size:10px;color:#74819a;font-weight:850}.live-execution-list{display:grid;gap:0;padding:8px 14px 11px}.live-stage{position:relative;display:grid;grid-template-columns:22px minmax(0,1fr);gap:8px;padding:8px 0}.live-stage:not(:last-child):after{content:"";position:absolute;right:10px;top:28px;bottom:-5px;width:1px;background:#dbe4f5}.live-stage-icon{position:relative;z-index:1;display:grid;place-items:center;width:21px;height:21px;border-radius:50%;background:#edf2ff;color:#315fc9;font-size:11px;font-weight:950}.live-stage.running .live-stage-icon{color:transparent}.live-stage.running .live-stage-icon:after{content:"";width:7px;height:7px;border-radius:50%;background:#3b6fe8;animation:liveDot .85s infinite alternate}.live-stage.completed .live-stage-icon{background:#e9f8f0;color:#12845a}.live-stage.blocked .live-stage-icon,.live-stage.failed .live-stage-icon{background:#fff0f1;color:#bd3640}.live-stage h4{margin:1px 0 0;font-size:12px}.live-stage p{margin:3px 0 0;color:#74819a;font-size:11px;line-height:1.55}.live-evidence{display:flex;flex-wrap:wrap;gap:5px;margin-top:6px}.live-evidence span{padding:3px 6px;border-radius:7px;background:#eef3ff;color:#315fc9;font-size:9px;font-weight:850}.live-execution-empty{padding:13px;color:#74819a;font-size:11px}@keyframes livePulse{70%{box-shadow:0 0 0 8px rgba(59,111,232,0)}}@keyframes liveDot{to{opacity:.35;transform:scale(.72)}}
  `;
  document.head.appendChild(style);

  function executionId() {
    if (window.crypto?.randomUUID) return window.crypto.randomUUID();
    return `exec_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 14)}`;
  }

  function isAsk(url, init) {
    try {
      const target = new URL(typeof url === 'string' ? url : url.url, window.location.href);
      const method = String(init?.method || (typeof url !== 'string' && url.method) || 'GET').toUpperCase();
      return target.origin === window.location.origin && target.pathname === '/ask' && method === 'POST';
    } catch (_) { return false; }
  }

  function createCard(id) {
    const messages = document.getElementById('businessMessages');
    if (!messages) return null;
    const card = document.createElement('article');
    card.className = 'live-execution';
    card.dataset.executionId = id;
    card.innerHTML = `
      <div class="live-execution-head">
        <div class="live-execution-title"><span class="live-execution-pulse"></span><span>تنفيذ أمير المرئي</span></div>
        <span class="live-execution-state">بدأ الآن</span>
      </div>
      <div class="live-execution-list"><div class="live-execution-empty">جارٍ فتح مسار التنفيذ…</div></div>`;
    messages.append(card);
    messages.scrollTop = messages.scrollHeight;
    cards.set(id, card);
    return card;
  }

  function evidenceChips(evidence) {
    if (!evidence || typeof evidence !== 'object') return '';
    const values = [];
    if (evidence.worker_id) values.push(`العامل: ${evidence.worker_id}`);
    if (evidence.completed_units) values.push(`${evidence.completed_units} خطوة`);
    if (evidence.file_count) values.push(`${evidence.file_count} ملف`);
    if (evidence.test_count) values.push(`${evidence.test_count} اختبار`);
    (Array.isArray(evidence.files) ? evidence.files.slice(0, 4) : []).forEach(file => values.push(file));
    return values.length ? `<div class="live-evidence">${values.map(value => `<span>${esc(value)}</span>`).join('')}</div>` : '';
  }

  function render(id, payload) {
    const card = cards.get(id) || createCard(id);
    if (!card) return;
    const stages = Array.isArray(payload.stages) ? payload.stages : [];
    const status = payload.status || 'running';
    card.className = `live-execution ${status}`;
    const state = card.querySelector('.live-execution-state');
    state.textContent = status === 'completed' ? 'اكتمل' : status === 'blocked' ? 'متوقف' : status === 'failed' ? 'فشل' : 'يعمل الآن';
    const list = card.querySelector('.live-execution-list');
    list.innerHTML = stages.length ? stages.map(stage => {
      const stageStatus = ['running', 'completed', 'blocked', 'failed'].includes(stage.status) ? stage.status : 'running';
      const icon = stageStatus === 'completed' ? '✓' : stageStatus === 'blocked' ? '!' : stageStatus === 'failed' ? '×' : '•';
      return `<div class="live-stage ${stageStatus}"><span class="live-stage-icon">${icon}</span><div><h4>${esc(stage.title)}</h4>${stage.detail ? `<p>${esc(stage.detail)}</p>` : ''}${evidenceChips(stage.evidence)}</div></div>`;
    }).join('') : '<div class="live-execution-empty">جارٍ فتح مسار التنفيذ…</div>';
    const messages = document.getElementById('businessMessages');
    if (messages && messages.scrollHeight - messages.scrollTop - messages.clientHeight < 180) messages.scrollTop = messages.scrollHeight;
    if (terminal.has(status)) stop(id);
  }

  async function refresh(id) {
    try {
      const response = await nativeFetch(`/ui/executions/${encodeURIComponent(id)}`, { cache: 'no-store' });
      if (response.status === 404) return;
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      render(id, await response.json());
    } catch (_) {
      // A temporary polling failure does not replace the real /ask result.
    }
  }

  function start(id) {
    createCard(id);
    refresh(id);
    const timer = window.setInterval(() => refresh(id), 650);
    timers.set(id, timer);
    window.setTimeout(() => {
      if (!timers.has(id)) return;
      const card = cards.get(id);
      if (card) card.querySelector('.live-execution-state').textContent = 'استغرق وقتًا أطول من المتوقع';
      stop(id);
    }, 180000);
  }

  function stop(id) {
    const timer = timers.get(id);
    if (timer) window.clearInterval(timer);
    timers.delete(id);
  }

  function markNetworkFailure(id, message) {
    const card = cards.get(id) || createCard(id);
    if (!card) return;
    card.className = 'live-execution failed';
    card.querySelector('.live-execution-state').textContent = 'تعذر الاتصال';
    card.querySelector('.live-execution-list').innerHTML = `<div class="live-stage failed"><span class="live-stage-icon">×</span><div><h4>انقطع الاتصال بمسار التنفيذ</h4><p>${esc(message || 'خطأ شبكة')}</p></div></div>`;
    stop(id);
  }

  window.fetch = async function (input, init = {}) {
    if (!isAsk(input, init)) return nativeFetch(input, init);
    const id = executionId();
    const headers = new Headers(init.headers || (typeof input !== 'string' ? input.headers : undefined));
    headers.set('X-Ameer-Execution-ID', id);
    const nextInit = { ...init, headers };
    start(id);
    try {
      const response = await nativeFetch(input, nextInit);
      await refresh(id);
      if (!response.ok) markNetworkFailure(id, `أعاد الخادم حالة HTTP ${response.status}`);
      return response;
    } catch (error) {
      markNetworkFailure(id, error?.message || 'خطأ شبكة');
      throw error;
    }
  };
})();
