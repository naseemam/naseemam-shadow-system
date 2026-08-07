"""
task_decomposer.py
==================
TaskDecomposer — يحوّل أمرًا بشريًا إلى Task Batch قابل للتنفيذ.

المسار:
    human_command
        ↓
    ExecutiveBrain (intent detection)
        ↓
    TaskDecomposer (task generation)
        ↓
    [Task, Task, Task, ...]

مثال:
    "ابنِ الصفحة الرئيسية"
        ↓
    [
        {id: "home-html", action: "write", executor: "file", target: "...", content: "..."},
        {id: "home-css",  action: "write", executor: "file", target: "...", content: "..."},
        {id: "home-js",   action: "write", executor: "file", target: "...", content: "..."},
    ]
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List


# ── Intent patterns ────────────────────────────────────────────────────────────

_BUILD_HOME_PATTERNS = [
    # Arabic
    "ابن", "ابنِ", "ابنى", "بناء", "اصنع", "اصنعي",
    "الصفحة الرئيسية", "صفحة رئيسية", "الهوم", "homepage",
    # English
    "build", "create", "make", "generate",
]

_HOME_PAGE_HINTS = [
    "الصفحة الرئيسية", "صفحة رئيسية", "الرئيسية", "هوم", "home", "homepage",
    "index", "landing",
]


def _matches(text: str, patterns: list[str]) -> bool:
    lower = text.lower()
    return any(p.lower() in lower for p in patterns)


def _detect_intent(command: str) -> str:
    """تحديد النية من الأمر البشري. يُعيد معرّف النية."""
    if _matches(command, _HOME_PAGE_HINTS) or (
        _matches(command, _BUILD_HOME_PATTERNS) and
        any(h.lower() in command.lower() for h in _HOME_PAGE_HINTS)
    ):
        return "build_homepage"

    if _matches(command, ["build", "ابن", "ابنِ", "اصنع", "بناء", "أنشئ", "انشئ", "أنشئي", "صمم", "اعمل", "create", "make", "generate"]):
        return "build_generic"

    return "unknown"


# ── Content templates ──────────────────────────────────────────────────────────

_HOME_HTML = """\
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>أمير — الصفحة الرئيسية</title>
  <link rel="stylesheet" href="style.css" />
</head>
<body>
  <header class="site-header">
    <div class="logo">
      <span class="logo-icon">🤖</span>
      <span class="logo-text">أمير</span>
    </div>
    <nav>
      <a href="#about">من أنا؟</a>
      <a href="#capabilities">قدراتي</a>
      <a href="#contact">تواصل</a>
    </nav>
  </header>

  <main>
    <section class="hero">
      <h1>مرحباً، أنا <span class="highlight">أمير</span></h1>
      <p class="subtitle">مساعدك الذكي — أفهم أوامرك وأنفّذها.</p>
      <div class="badges">
        <span class="badge">⚡ تنفيذ فوري</span>
        <span class="badge">🧠 ذاكرة دائمة</span>
        <span class="badge">🔐 حوكمة آمنة</span>
      </div>
    </section>

    <section id="about" class="card-section">
      <h2>من أنا؟</h2>
      <p>
        أنا نظام ذكاء اصطناعي تنفيذي مبني خصيصاً لـ نسيم.
        أحوّل الأوامر البشرية إلى مهام قابلة للتنفيذ عبر Pipeline متكامل.
      </p>
    </section>

    <section id="capabilities" class="card-section">
      <h2>قدراتي</h2>
      <div class="capabilities-grid">
        <div class="cap-card">
          <span class="cap-icon">📋</span>
          <h3>Task Decomposer</h3>
          <p>أكسر أي أمر إلى مهام واضحة</p>
        </div>
        <div class="cap-card">
          <span class="cap-icon">✅</span>
          <h3>Plan Validator</h3>
          <p>أتحقق من كل مهمة قبل التنفيذ</p>
        </div>
        <div class="cap-card">
          <span class="cap-icon">📅</span>
          <h3>Scheduler</h3>
          <p>أرتّب المهام بالأولوية الصحيحة</p>
        </div>
        <div class="cap-card">
          <span class="cap-icon">💾</span>
          <h3>File Executor</h3>
          <p>أكتب الملفات الحقيقية في البيئة</p>
        </div>
      </div>
    </section>

    <section id="contact" class="card-section">
      <h2>تواصل معي</h2>
      <p>أرسل لي أمرًا عبر الواجهة وسأنفّذه فورًا.</p>
    </section>
  </main>

  <footer>
    <p>أمير © 2025 — Proof of Execution</p>
  </footer>
  <script src="script.js"></script>
</body>
</html>
"""

_HOME_CSS = """\
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --bg: #f5f7fa;
  --surface: #ffffff;
  --border: #e2e8f0;
  --ink: #0f172a;
  --muted: #64748b;
  --accent: #2563eb;
  --accent-light: #eff6ff;
  --success: #16a34a;
  --radius: 14px;
  --shadow: 0 2px 12px rgba(0,0,0,.08);
}

html, body {
  font-family: "Segoe UI", Tahoma, "Arabic UI Text", Arial, sans-serif;
  background: var(--bg);
  color: var(--ink);
  line-height: 1.6;
  font-size: 16px;
}

/* ─── Header ─── */
.site-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 2rem;
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  position: sticky;
  top: 0;
  z-index: 10;
}

.logo { display: flex; align-items: center; gap: .5rem; font-size: 1.3rem; font-weight: 700; }
.logo-icon { font-size: 1.5rem; }

nav a {
  color: var(--muted);
  text-decoration: none;
  margin-inline-start: 1.5rem;
  font-size: .9rem;
  transition: color .2s;
}
nav a:hover { color: var(--accent); }

/* ─── Hero ─── */
.hero {
  text-align: center;
  padding: 4rem 1rem 3rem;
  max-width: 700px;
  margin: 0 auto;
}

.hero h1 { font-size: 2.4rem; font-weight: 800; margin-bottom: .75rem; }
.highlight { color: var(--accent); }
.subtitle { font-size: 1.15rem; color: var(--muted); margin-bottom: 1.5rem; }

.badges { display: flex; justify-content: center; gap: .6rem; flex-wrap: wrap; }
.badge {
  background: var(--accent-light);
  color: var(--accent);
  border: 1px solid #bfdbfe;
  border-radius: 999px;
  padding: .25rem .85rem;
  font-size: .85rem;
  font-weight: 600;
}

/* ─── Sections ─── */
main { max-width: 900px; margin: 0 auto; padding: 1rem 1.5rem 3rem; }

.card-section {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 2rem;
  margin-bottom: 1.5rem;
  box-shadow: var(--shadow);
}

.card-section h2 { font-size: 1.4rem; font-weight: 700; margin-bottom: 1rem; }
.card-section p { color: var(--muted); }

/* ─── Capabilities grid ─── */
.capabilities-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 1rem;
  margin-top: .5rem;
}

.cap-card {
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 1.25rem;
  text-align: center;
  transition: transform .2s, box-shadow .2s;
}
.cap-card:hover { transform: translateY(-3px); box-shadow: 0 6px 20px rgba(0,0,0,.1); }
.cap-icon { font-size: 2rem; display: block; margin-bottom: .5rem; }
.cap-card h3 { font-size: .95rem; font-weight: 700; margin-bottom: .3rem; color: var(--accent); }
.cap-card p { font-size: .83rem; color: var(--muted); }

/* ─── Footer ─── */
footer {
  text-align: center;
  padding: 2rem;
  color: var(--muted);
  font-size: .85rem;
  border-top: 1px solid var(--border);
}
"""

_HOME_JS = """\
/* Ameer Home — script.js */

document.addEventListener('DOMContentLoaded', () => {
  // Smooth scroll for nav links
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', e => {
      e.preventDefault();
      const target = document.querySelector(anchor.getAttribute('href'));
      if (target) {
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    });
  });

  // Animate capability cards on scroll
  const cards = document.querySelectorAll('.cap-card');
  const observer = new IntersectionObserver(
    entries => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.style.opacity = '1';
          entry.target.style.transform = 'translateY(0)';
        }
      });
    },
    { threshold: 0.1 }
  );

  cards.forEach(card => {
    card.style.opacity = '0';
    card.style.transform = 'translateY(20px)';
    card.style.transition = 'opacity .4s ease, transform .4s ease';
    observer.observe(card);
  });

  console.log('[Ameer] Home page loaded — Proof of Execution active.');
});
"""


# ── TaskDecomposer ─────────────────────────────────────────────────────────────

class TaskDecomposer:
    """
    يحوّل أمرًا بشريًا إلى Task Batch.

    الاستخدام:
    ----------
    decomposer = TaskDecomposer(workspace_root=ROOT)
    result = decomposer.decompose("ابنِ الصفحة الرئيسية")

    result = {
        "intent": "build_homepage",
        "command": "ابنِ الصفحة الرئيسية",
        "tasks": [ {...}, {...}, {...} ],
        "task_count": 3,
        "decomposed_at": "2025-...",
    }
    """

    RUNTIME_PREFIX = "09_Assets/runtime_workspace"

    def __init__(self, workspace_root: str) -> None:
        self._root = workspace_root

    def decompose(self, command: str) -> Dict[str, Any]:
        """يحلّل الأمر ويُعيد task batch جاهزًا للتنفيذ."""
        intent = _detect_intent(command)
        tasks = self._build_tasks(intent, command)
        return {
            "intent": intent,
            "command": command,
            "tasks": tasks,
            "task_count": len(tasks),
            "decomposed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

    # ── private ───────────────────────────────────────────────────────────────

    def _build_tasks(self, intent: str, command: str) -> List[Dict[str, Any]]:
        if intent == "build_homepage":
            return self._homepage_tasks()
        if intent == "build_generic":
            return self._generic_page_tasks(command)
        # Fallback — return an empty-but-valid placeholder
        return []

    def _homepage_tasks(self) -> List[Dict[str, Any]]:
        prefix = f"{self.RUNTIME_PREFIX}/home"
        return [
            {
                "id": f"home-html-{uuid.uuid4().hex[:6]}",
                "action": "write",
                "executor": "file",
                "target": f"{prefix}/index.html",
                "content": _HOME_HTML,
                "priority": "high",
                "description": "كتابة index.html — هيكل الصفحة الرئيسية",
            },
            {
                "id": f"home-css-{uuid.uuid4().hex[:6]}",
                "action": "write",
                "executor": "file",
                "target": f"{prefix}/style.css",
                "content": _HOME_CSS,
                "priority": "high",
                "description": "كتابة style.css — تنسيق الصفحة الرئيسية",
            },
            {
                "id": f"home-js-{uuid.uuid4().hex[:6]}",
                "action": "write",
                "executor": "file",
                "target": f"{prefix}/script.js",
                "content": _HOME_JS,
                "priority": "normal",
                "description": "كتابة script.js — سلوك الصفحة الرئيسية",
            },
        ]

    @staticmethod
    def _slugify(text: str) -> str:
        """تحويل نص عربي/إنجليزي إلى slug آمن للمسارات."""
        import re as _re
        slug = text.strip()
        # Replace spaces and common separators with hyphens
        slug = _re.sub(r"[\s_/\\]+", "-", slug)
        # Remove characters that are unsafe in file paths
        slug = _re.sub(r"[^\w\u0600-\u06FF\-]", "", slug)
        slug = slug.strip("-") or "project"
        return slug[:60]

    def _generic_page_tasks(self, command: str) -> List[Dict[str, Any]]:
        slug = self._slugify(command)
        prefix = f"{self.RUNTIME_PREFIX}/projects/{slug}"
        html_content = f"""\
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{command}</title>
  <link rel="stylesheet" href="style.css" />
</head>
<body>
  <main class="page-wrapper">
    <h1 class="page-title">{command}</h1>
    <p class="page-subtitle">أُنشئت بواسطة أمير</p>
  </main>
  <script src="script.js"></script>
</body>
</html>"""
        css_content = """\
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: 'Segoe UI', Tahoma, Arial, sans-serif;
  background: #f8f9fa;
  color: #212529;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
}
.page-wrapper {
  text-align: center;
  padding: 3rem 2rem;
  max-width: 700px;
}
.page-title {
  font-size: 2.5rem;
  font-weight: 700;
  margin-bottom: 1rem;
  color: #1a1a2e;
}
.page-subtitle {
  font-size: 1.1rem;
  color: #6c757d;
}"""
        js_content = """\
document.addEventListener('DOMContentLoaded', function () {
  console.log('[Ameer] Project page loaded.');
});"""
        return [
            {
                "id": f"page-html-{uuid.uuid4().hex[:6]}",
                "action": "write",
                "executor": "file",
                "target": f"{prefix}/index.html",
                "content": html_content,
                "priority": "high",
                "description": f"كتابة index.html لـ: {command}",
            },
            {
                "id": f"page-css-{uuid.uuid4().hex[:6]}",
                "action": "write",
                "executor": "file",
                "target": f"{prefix}/style.css",
                "content": css_content,
                "priority": "high",
                "description": f"كتابة style.css لـ: {command}",
            },
            {
                "id": f"page-js-{uuid.uuid4().hex[:6]}",
                "action": "write",
                "executor": "file",
                "target": f"{prefix}/script.js",
                "content": js_content,
                "priority": "normal",
                "description": f"كتابة script.js لـ: {command}",
            },
        ]
