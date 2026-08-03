(function () {
  const STORAGE_KEY = 'ameer_workspace_v2';
  const SECTION_STORAGE_KEY = 'ameer_active_section';
  const DEFAULT_PROJECTS = ['Ameer', 'حلم الندى', 'الاستثمار'];
  const navItems = [
    { key: 'home', label: 'Home', icon: '🏠' },
    { key: 'executive-chat', label: 'Executive Chat', icon: '💬' },
    { key: 'projects', label: 'Projects', icon: '📁' },
    { key: 'memory', label: 'Memory', icon: '🧠' },
    { key: 'development', label: 'Development', icon: '🛠' },
    { key: 'websites', label: 'Websites', icon: '🌐' },
    { key: 'business', label: 'Business', icon: '💼' },
    { key: 'investment', label: 'Investment', icon: '📈' },
    { key: 'bots', label: 'Bots', icon: '🤖' },
    { key: 'system', label: 'System', icon: '⚙️' },
    { key: 'services', label: 'services', icon: '🌐' },
    { key: 'pricing', label: 'pricing', icon: '🌐' },
    { key: 'about', label: 'about', icon: '🌐' },
    { key: 'contact', label: 'contact', icon: '🌐' },
  ];

  const state = {
    conversations: [],
    activeConversationId: null,
    activePage: 'home',
    activeProject: 'Ameer',
    search: '',
    lastReply: null,
    docs: []
  };

  function loadState() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return null;
      return JSON.parse(raw);
    } catch {
      return null;
    }
  }

  function saveState() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  }

  function loadSectionSelection() {
    try {
      const saved = localStorage.getItem(SECTION_STORAGE_KEY);
      return saved || 'home';
    } catch {
      return 'home';
    }
  }

  function saveSectionSelection(sectionKey) {
    localStorage.setItem(SECTION_STORAGE_KEY, sectionKey);
  }

  function applyTheme(theme) {
    const resolved = theme === 'dark' ? 'dark' : 'light';
    document.documentElement.setAttribute('data-theme', resolved);
    localStorage.setItem('ameer-theme', resolved);
    const btn = document.getElementById('themeToggleBtn');
    if (btn) {
      btn.textContent = resolved === 'dark' ? '☀️ Light' : '🌗 Theme';
    }
  }

  function createConversation(title = 'محادثة جديدة', project = 'Ameer') {
    const convo = {
      id: Date.now().toString(36),
      title,
      project,
      pinned: false,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      messages: []
    };
    state.conversations.unshift(convo);
    state.activeConversationId = convo.id;
    saveState();
    return convo;
  }

  function getActiveConversation() {
    return state.conversations.find(c => c.id === state.activeConversationId) || null;
  }

  function ensureDefaultConversation() {
    if (!state.conversations.length) {
      createConversation('محادثة جديدة', state.activeProject);
    }
    if (!state.activeConversationId) {
      state.activeConversationId = state.conversations[0].id;
    }
  }

  function updateConversation(updater) {
    const convo = getActiveConversation();
    if (!convo) return;
    updater(convo);
    convo.updatedAt = new Date().toISOString();
    saveState();
    render();
  }

  function appendMessage(role, text) {
    updateConversation(convo => {
      convo.messages.push({ role, text, createdAt: new Date().toISOString() });
    });
  }

  function replaceLastSystemMessage(text) {
    updateConversation(convo => {
      for (let index = convo.messages.length - 1; index >= 0; index -= 1) {
        if (convo.messages[index].role === 'system') {
          convo.messages[index].text = text;
          convo.messages[index].createdAt = new Date().toISOString();
          return;
        }
      }
      convo.messages.push({ role: 'system', text, createdAt: new Date().toISOString() });
    });
  }

  function setConversationTitleFromPrompt(text) {
    const convo = getActiveConversation();
    if (!convo || convo.title !== 'محادثة جديدة') return;
    const base = text.trim().replace(/\s+/g, ' ').slice(0, 38);
    convo.title = base || 'محادثة جديدة';
    convo.updatedAt = new Date().toISOString();
    saveState();
    render();
  }

  function escapeHtml(text) {
    return String(text || '')
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
      .replaceAll("'", '&#039;');
  }

  function formatTime(iso) {
    const d = new Date(iso);
    return d.toLocaleTimeString('ar-SA', { hour: '2-digit', minute: '2-digit' });
  }

  function renderNavigation() {
    const host = document.getElementById('pageTabs');
    if (!host) return;
    host.innerHTML = navItems.map(item => `
      <button class="tab ${state.activePage === item.key ? 'active' : ''}" data-page="${item.key}" type="button">${item.icon} ${item.label}</button>
    `).join('');
    host.querySelectorAll('.tab').forEach(btn => {
      btn.addEventListener('click', () => {
        const nextPage = btn.getAttribute('data-page');
        state.activePage = nextPage;
        saveSectionSelection(nextPage);
        saveState();
        render();
      });
    });
  }

  function renderSidebar() {
    const filtered = state.conversations.filter(c => {
      const term = state.search.trim().toLowerCase();
      if (!term) return true;
      return [c.title, c.project, ...(c.messages || []).map(m => m.text)].join(' ').toLowerCase().includes(term);
    });

    const conversationHost = document.getElementById('conversationList');
    if (conversationHost) {
      conversationHost.innerHTML = filtered.map(convo => `
        <div class="conversation-item ${convo.id === state.activeConversationId ? 'active' : ''}" data-id="${convo.id}">
          <div class="meta-row">
            <span>${escapeHtml(convo.project || 'Ameer')}</span>
            <span>${convo.pinned ? '⭐' : ''}</span>
          </div>
          <div class="title-row">
            <strong>${escapeHtml(convo.title || 'محادثة جديدة')}</strong>
            <span class="pill">${escapeHtml(formatTime(convo.updatedAt))}</span>
          </div>
        </div>
      `).join('');
    }

    const projectHost = document.getElementById('projectList');
    if (projectHost) {
      projectHost.innerHTML = DEFAULT_PROJECTS.map(project => `
        <div class="doc-item">${escapeHtml(project)}</div>
      `).join('');
    }

    document.querySelectorAll('.conversation-item').forEach(item => {
      item.addEventListener('click', () => {
        state.activeConversationId = item.getAttribute('data-id');
        saveState();
        render();
      });
    });
  }

  function renderWorkspaceContainers() {
    document.querySelectorAll('.page-view').forEach(view => {
      const key = view.id.replace('view-', '');
      view.classList.toggle('active', state.activePage === key);
    });

    const moduleKeyMap = {
      'executive-chat': 'executive_chat'
    };
    const activeKey = moduleKeyMap[state.activePage] || state.activePage;
    if (window.AmeerWorkspaceLoader && typeof window.AmeerWorkspaceLoader.load === 'function') {
      window.AmeerWorkspaceLoader.load(activeKey);
    }

    const contentHost = document.querySelector('.content');
    if (contentHost) {
      contentHost.style.display = 'grid';
      contentHost.style.gap = '12px';
      contentHost.style.alignContent = 'start';
    }
  }

  function renderHeader() {
    const convo = getActiveConversation();
    const pageMap = {
      home: ['Home', 'Ameer OS · الصفحة الرئيسية'],
      'executive-chat': ['Executive Chat', 'Ameer OS · المحادثة التنفيذية'],
      projects: ['Projects', 'Ameer OS · المشاريع'],
      memory: ['Memory', 'Ameer OS · الذاكرة'],
      development: ['Development', 'Ameer OS · التطوير'],
      websites: ['Websites', 'Ameer OS · المواقع'],
      business: ['Business', 'Ameer OS · الأعمال'],
      investment: ['Investment', 'Ameer OS · الاستثمار'],
      bots: ['Bots', 'Ameer OS · الروبوتات'],
      system: ['System', 'Ameer OS · النظام'],
      services: ['services', 'Ameer OS · services'],
      pricing: ['pricing', 'Ameer OS · pricing'],
      about: ['about', 'Ameer OS · about'],
      contact: ['contact', 'Ameer OS · contact'],
    };
    const [title, sub] = pageMap[state.activePage] || pageMap.home;
    const titleHost = document.getElementById('currentConversationTitle');
    const metaHost = document.getElementById('currentConversationMeta');
    const pinHost = document.getElementById('pinConversationBtn');
    if (titleHost) {
      titleHost.textContent = title;
    }
    if (metaHost) {
      metaHost.textContent = convo ? `${sub} · ${convo.project || 'Ameer'}` : sub;
    }
    if (pinHost) {
      pinHost.textContent = convo && convo.pinned ? '⭐ مثبت' : '⭐ تثبيت';
    }
  }

  function renderMessages() {
    const host = document.getElementById('messageArea');
    if (!host) return;

    const convo = getActiveConversation();
    const messages = convo?.messages || [];
    const content = messages.length
      ? messages.map(message => {
          const roleLabel = message.role === 'user' ? 'أنت' : message.role === 'assistant' ? 'أمير' : 'النظام';
          const bubbleClass = message.role === 'user' ? 'bubble user' : message.role === 'assistant' ? 'bubble assistant' : 'bubble system';
          return `
            <div class="${bubbleClass}">
              <div class="meta">${escapeHtml(roleLabel)} · ${escapeHtml(formatTime(message.createdAt))}</div>
              <div>${escapeHtml(message.text || '')}</div>
            </div>
          `;
        }).join('')
      : '<div class="bubble system">ابدأ بالكتابة وسأرد داخل هذه المحادثة.</div>';

    host.innerHTML = content;
    host.style.display = 'grid';
    host.style.gap = '10px';
    host.style.alignContent = 'start';
  }

  function renderDetail(j) {
    const summary = document.getElementById('summary');
    const executionResult = document.getElementById('executionResult');
    const executionProgress = document.getElementById('executionProgress');
    const results = document.getElementById('results');
    const trace = document.getElementById('trace');
    if (!j) {
      summary.innerHTML = 'سيظهر رد أمير هنا.';
      executionResult.innerHTML = '';
      executionProgress.innerHTML = '';
      results.innerHTML = '';
      trace.innerHTML = '';
      return;
    }
    summary.innerHTML = `<div>${escapeHtml(j.reply || j.message || 'تمت المعالجة.')}</div>`;
    executionResult.innerHTML = '';
    executionProgress.innerHTML = '';
    results.innerHTML = '';
    trace.innerHTML = '';
  }

  function render() {
    ensureDefaultConversation();
    renderNavigation();
    renderSidebar();
    renderHeader();
    renderMessages();
    renderWorkspaceContainers();
    renderDetail(state.lastReply);
  }

  function protectWorkspaceAccess() {
    return true;
  }

  async function checkHealth() {
    try {
      const r = await fetch('/health');
      const j = await r.json();
      const el = document.getElementById('serverStatus');
      const buildEl = document.getElementById('buildIdBadge');
      if (el) {
        el.textContent = `متصل · ${j.documents} مستند`;
        el.className = 'status-pill';
      }
      if (buildEl) {
        buildEl.textContent = `build: ${j.build_id || 'unknown'}`;
      }
      state.docs = Array.isArray(j.files) ? j.files : [];
    } catch {
      const el = document.getElementById('serverStatus');
      if (el) {
        el.textContent = 'الخادم غير متاح';
        el.className = 'status-pill warn';
      }
    }
    render();
  }

  function submitPrompt(text, options = {}) {
    const input = document.getElementById('q');
    if (!input) return false;
    input.value = text;
    if (options.focus !== false) {
      input.focus();
    }
    if (options.send !== false) {
      ask();
    }
    return true;
  }

  async function ask() {
    if (!protectWorkspaceAccess()) return;
    const q = document.getElementById('q').value.trim();
    const btn = document.getElementById('askBtn');
    if (!q) return;
    ensureDefaultConversation();
    setConversationTitleFromPrompt(q);
    appendMessage('user', q);
    document.getElementById('q').value = '';
    if (btn) {
      btn.disabled = true;
    }
    try {
      const r = await fetch('/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json; charset=utf-8' },
        body: JSON.stringify({ query: q, max_results: 8 })
      });
      const j = await r.json();
      const reply = j.reply || j.message || 'تمت المعالجة.';
      appendMessage('assistant', reply);
      state.lastReply = j;
      renderDetail(j);
    } catch (e) {
      appendMessage('assistant', `حدث خطأ: ${String(e)}`);
    } finally {
      if (btn) {
        btn.disabled = false;
      }
    }
  }

  function bindEvents() {
    const themeBtn = document.getElementById('themeToggleBtn');
    if (themeBtn) {
      themeBtn.addEventListener('click', () => {
        const next = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
        applyTheme(next);
      });
    }

    const newConversationBtn = document.getElementById('newConversationBtn');
    if (newConversationBtn) {
      newConversationBtn.addEventListener('click', () => {
        if (!protectWorkspaceAccess()) return;
        createConversation('محادثة جديدة', state.activeProject);
        render();
      });
    }

    const conversationSearch = document.getElementById('conversationSearch');
    if (conversationSearch) {
      conversationSearch.addEventListener('input', e => {
        state.search = e.target.value;
        renderSidebar();
      });
    }

    const pinConversationBtn = document.getElementById('pinConversationBtn');
    if (pinConversationBtn) {
      pinConversationBtn.addEventListener('click', () => {
        if (!protectWorkspaceAccess()) return;
        const convo = getActiveConversation();
        if (!convo) return;
        convo.pinned = !convo.pinned;
        saveState();
        render();
      });
    }

    const renameConversationBtn = document.getElementById('renameConversationBtn');
    if (renameConversationBtn) {
      renameConversationBtn.addEventListener('click', () => {
        if (!protectWorkspaceAccess()) return;
        const convo = getActiveConversation();
        if (!convo) return;
        const title = prompt('أدخل اسم المحادثة الجديدة:', convo.title || 'محادثة جديدة');
        if (title && title.trim()) {
          convo.title = title.trim();
          saveState();
          render();
        }
      });
    }

    const deleteConversationBtn = document.getElementById('deleteConversationBtn');
    if (deleteConversationBtn) {
      deleteConversationBtn.addEventListener('click', () => {
        if (!protectWorkspaceAccess()) return;
        const convo = getActiveConversation();
        if (!convo) return;
        if (!confirm('هل تريد حذف هذه المحادثة؟')) return;
        state.conversations = state.conversations.filter(c => c.id !== convo.id);
        state.activeConversationId = state.conversations[0]?.id || null;
        saveState();
        render();
      });
    }

    const askButton = document.getElementById('askBtn');
    if (askButton) {
      askButton.addEventListener('click', ask);
    }

    const input = document.getElementById('q');
    if (input) {
      input.addEventListener('keydown', e => {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          ask();
        }
      });
    }
  }

  function init() {
    const saved = loadState();
    if (saved) {
      Object.assign(state, saved);
    }
    const storedTheme = localStorage.getItem('ameer-theme') || 'light';
    applyTheme(storedTheme);
    const storedSection = loadSectionSelection();
    if (navItems.some(item => item.key === storedSection)) {
      state.activePage = storedSection;
    }
    if (!state.conversations.length) {
      createConversation('محادثة جديدة', state.activeProject);
    }
    state.activeConversationId = state.activeConversationId || state.conversations[0].id;
    bindEvents();
    render();
    setTimeout(() => render(), 50);
    checkHealth();
  }

  function openPage(pageKey) {
    if (window.AmeerRouter && typeof window.AmeerRouter.navigate === 'function') {
      window.AmeerRouter.navigate(pageKey || 'home');
      state.activePage = pageKey || 'home';
      saveSectionSelection(state.activePage);
      saveState();
      render();
      return true;
    }
    return false;
  }

  window.AmeerWorkspaceShell = {
    init,
    render,
    openPage,
    sendPrompt: submitPrompt,
    getState: function () {
      return state;
    }
  };
})();
