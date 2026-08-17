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

import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

try:
    from kernel.arabic_intent_lexicon import classify_arabic_intent
except ImportError:  # direct module loading in legacy tests
    from arabic_intent_lexicon import classify_arabic_intent


# ── Intent patterns ────────────────────────────────────────────────────────────

_BUILD_HOME_PATTERNS = [
    # Arabic
    "ابن", "ابنِ", "ابنى", "بناء", "اصنع", "اصنعي",
    "أنشئ", "انشئ", "إنشاء",
    "الصفحة الرئيسية", "صفحة رئيسية", "الهوم", "homepage",
    # English
    "build", "create", "make", "generate",
]

_HOME_PAGE_HINTS = [
    "الصفحة الرئيسية", "صفحة رئيسية", "الرئيسية", "هوم", "home", "homepage",
    "index", "landing",
]

_UI_IMPROVEMENT_MARKERS = [
    "تحسين واجهة المستخدم", "تحسين الواجهة", "تحسين واجهة", "تحسين الصفحة",
    "حسّن الواجهة", "حسن الواجهة", "تطوير الواجهة", "تطوير واجهة",
    "improve ui", "improve the interface", "enhance frontend", "improve frontend",
]

# Markers that signal a read/display intent — must take priority over HOME_PAGE_HINTS
# so that "اقرأ .../home/index.html" is never misrouted to build_homepage.
_READ_MARKERS = [
    "اقرأ", "read", "show", "اعرض", "عرض", "contents", "محتوى", "content",
    "افتح", "open", "display",
]

_RUN_TEST_MARKERS = [
    "تشغيل الاختبارات", "شغّل الاختبارات", "شغل الاختبارات",
    "run test", "run tests", "pytest", "test",
    "اختبار", "اختبارات", "نفّذ الاختبارات", "نفذ الاختبارات",
]

# AEX-1: executable intents are explicit, auditable, and permission-aware.
# ``permission_mode`` is consumed by the execution boundary and is also exposed
# in the decomposition result so callers can explain why an action is allowed,
# tracked, pending, or denied.
AEX1_INTENT_SPECS = {
    "repository_review": {
        "description": "مراجعة المستودع قراءةً وتحليلاً دون آثار جانبية",
        "permission_mode": "read_only",
        "capability": "analysis",
        "requires_approval": False,
    },
    "code_edit": {
        "description": "تعديل كود داخل مساحة العمل مع تتبع",
        "permission_mode": "tracked_write",
        "capability": "programming",
        "requires_approval": False,
    },
    "build_website": {
        "description": "بناء موقع جديد داخل مساحة العمل",
        "permission_mode": "tracked_write",
        "capability": "programming",
        "requires_approval": False,
    },
    "build_homepage": {
        "description": "تحسين أو بناء واجهة الصفحة الرئيسية داخل مساحة العمل",
        "permission_mode": "tracked_write",
        "capability": "programming",
        "requires_approval": False,
    },
    "build_store": {
        "description": "بناء متجر جديد داخل مساحة العمل",
        "permission_mode": "tracked_write",
        "capability": "programming",
        "requires_approval": False,
    },
    "run_test": {
        "description": "تشغيل الاختبارات محلياً",
        "permission_mode": "read_only",
        "capability": "shell_execution",
        "requires_approval": False,
    },
    "execute_pending_tasks": {
        "description": "تنفيذ المهام المعلّقة المسجلة في الحالة التنفيذية",
        "permission_mode": "tracked_execution",
        "requires_approval": False,
    },
    "open_branch": {
        "description": "فتح فرع Git جديد",
        "permission_mode": "external_approval",
        "capability": "engineering",
        "requires_approval": True,
    },
    "open_pull_request": {
        "description": "فتح طلب سحب على GitHub",
        "permission_mode": "external_approval",
        "capability": "engineering",
        "requires_approval": True,
    },
    "deploy_railway": {
        "description": "النشر على Railway",
        "permission_mode": "external_approval",
        "capability": "engineering",
        "requires_approval": True,
    },
}

_REPOSITORY_REVIEW_MARKERS = [
    "راجع المستودع", "مراجعة المستودع", "راجع الكود", "حلل المستودع",
    "repository review", "review repository", "review the repo", "audit repository",
]
_CODE_EDIT_MARKERS = [
    "عدل الكود", "عدّل الكود", "تعديل الكود", "صلح الكود", "إصلاح الكود",
    "edit code", "modify code", "fix code", "refactor",
]
_BUILD_STORE_MARKERS = [
    "ابن متجر", "ابنِ متجر", "أنشئ متجر", "انشئ متجر", "بناء متجر",
    "build store", "create store", "ecommerce", "e-commerce", "متجر إلكتروني", "متجر الكتروني",
]
_BUILD_WEBSITE_MARKERS = [
    "ابن موقع", "ابنِ موقع", "أنشئ موقع", "انشئ موقع", "بناء موقع",
    "build website", "create website", "new website", "موقع جديد",
]
_EXECUTE_PENDING_TASKS_MARKERS = [
    # Single-word approvals (MUST come first for priority)
    "موافق", "موافقة", "نفّذ", "نفذ", "اوك", "ok", "yes", "نعم", "تمام",
    # Phrases
    "نفّذ المهام الآن", "نفذ المهام الآن", "نفّذ جميع المهام", "نفذ جميع المهام",
    "ابدأ المهام المعلقة", "ابدأ تنفيذ المهام", "شغّل المهام المعلقة", "شغل المهام المعلقة",
    "execute pending tasks", "execute all tasks", "run pending tasks",
]
_OPEN_BRANCH_MARKERS = [
    "افتح فرع", "أنشئ فرع", "انشئ فرع", "فتح فرع", "open branch", "create branch",
]
_OPEN_PR_MARKERS = [
    "افتح طلب سحب", "فتح طلب سحب", "أنشئ طلب سحب", "انشئ طلب سحب",
    "افتح pr", "open pull request", "open pr", "create pull request",
]
_DEPLOY_RAILWAY_MARKERS = [
    "انشر على railway", "انشر إلى railway", "النشر على railway", "railway",
    "deploy to railway", "deploy railway", "publish on railway",
]


def _matches(text: str, patterns: list[str]) -> bool:
    lower = text.lower()
    return any(p.lower() in lower for p in patterns)


def _has_read_intent(command: str) -> bool:
    """Return True when the command explicitly requests reading/displaying a file."""
    return _matches(command, _READ_MARKERS)


def _extract_read_target(command: str) -> str:
    """Extract the requested file path from an explicit read/display command."""
    patterns = (
        r"(?:اقرأ|read|show|اعرض|عرض|افتح|open|display)\s+(?:محتوى\s+|contents?\s+of\s+)?(?:ملف|file)?\s*[\"'“”]?([^\"'“”\s]+)[\"'“”]?",
        r"(?:ملف|file)\s+[\"'“”]?([^\"'“”\s]+)[\"'“”]?",
    )
    for pattern in patterns:
        match = re.search(pattern, command, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip(" .،؟")
    return ""


def normalize_arabic_for_match(text: str) -> str:
    value = (text or "").lower()
    return value.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").replace("ى", "ي")


def _detect_intent(command: str) -> str:
    """تحديد النية من الأمر البشري. يُعيد معرّف النية.

    ترتيب الأولوية:
    1. نية القراءة (file_read) — تأخذ الأولوية لمنع مسارات file-path مثل home/index
       من تشغيل build_homepage خطأً، وتُمرَّر لاحقًا عبر مسار التنفيذ المحكوم.
    2. run_test — تشغيل الاختبارات.
    3. build_homepage — يشترط وجود فعل بناء صريح أو ذكر الصفحة الرئيسية وحده.
    4. build_generic — أوامر البناء العامة.
    5. unknown — الاحتياطي.
    """
    # AEX-1 execution verbs such as "افتح فرعاً" must win over the generic
    # read marker "افتح". A file read still wins for explicit file/content reads.
    if _has_read_intent(command) and not _matches(command, _OPEN_BRANCH_MARKERS + _OPEN_PR_MARKERS):
        return "file_read"

    # AEX-1 execution intents take priority over generic build markers.
    if _matches(command, _EXECUTE_PENDING_TASKS_MARKERS):
        return "execute_pending_tasks"
    if _matches(command, _DEPLOY_RAILWAY_MARKERS):
        return "deploy_railway"
    if _matches(command, _OPEN_PR_MARKERS):
        return "open_pull_request"
    if _matches(command, _OPEN_BRANCH_MARKERS):
        return "open_branch"
    if _matches(command, _REPOSITORY_REVIEW_MARKERS):
        return "repository_review"

    # The unified lexicon adds only the missing UI improvement/design forms here;
    # it must not override explicit AEX-1 intents such as branch/PR/repository work.
    arabic = classify_arabic_intent(command)
    normalized_command = normalize_arabic_for_match(command)
    if arabic.intent == "write" and arabic.execution_candidate and any(
        token in normalized_command
        for token in ("واجهه", "واجهه", "صفحه", "موقع", "frontend", "ui", "html", "css")
    ) and any(
        token in normalized_command
        for token in ("تحسين", "حسن", "حسّن", "تطوير", "طور", "طوّر", "تصميم", "صمم", "صمّم")
    ):
        return "build_homepage"

    if _matches(command, _CODE_EDIT_MARKERS):
        return "code_edit"
    if _matches(command, _UI_IMPROVEMENT_MARKERS):
        return "build_homepage"
    if _matches(command, _BUILD_STORE_MARKERS):
        return "build_store"
    if _matches(command, _BUILD_WEBSITE_MARKERS):
        return "build_website"

    # Priority-2: test execution
    if _matches(command, _RUN_TEST_MARKERS):
        return "run_test"

    if _matches(command, _HOME_PAGE_HINTS) or (
        _matches(command, _BUILD_HOME_PATTERNS) and
        any(h.lower() in command.lower() for h in _HOME_PAGE_HINTS)
    ):
        return "build_homepage"

    if _matches(command, ["build", "ابن", "ابنِ", "اصنع", "بناء", "أنشئ", "انشئ"]):
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


# ── Generic page templates ────────────────────────────────────────────────────

_GENERIC_HTML_TPL = """\
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title}</title>
  <link rel="stylesheet" href="style.css" />
</head>
<body>
  <header class="page-header">
    <div class="logo"><span class="logo-icon">✨</span> <span class="logo-text">{title}</span></div>
  </header>

  <main>
    <section class="hero">
      <h1>{title}</h1>
      <p class="subtitle">{description}</p>
    </section>

    <section class="card-section">
      <h2>حول هذه الصفحة</h2>
      <p>{description}</p>
    </section>
  </main>

  <footer>
    <p>أُنشئت بواسطة أمير · {title}</p>
  </footer>
  <script src="script.js"></script>
</body>
</html>
"""

_GENERIC_CSS = """\
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --bg: #f5f7fa;
  --surface: #ffffff;
  --border: #e2e8f0;
  --ink: #0f172a;
  --muted: #64748b;
  --accent: #7c3aed;
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

.page-header {
  display: flex;
  align-items: center;
  padding: 1rem 2rem;
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  position: sticky;
  top: 0;
}

.logo { display: flex; align-items: center; gap: .5rem; font-size: 1.2rem; font-weight: 700; }

.hero {
  text-align: center;
  padding: 4rem 1rem 2rem;
  max-width: 700px;
  margin: 0 auto;
}

.hero h1 { font-size: 2.2rem; font-weight: 800; margin-bottom: .75rem; color: var(--accent); }
.subtitle { font-size: 1.1rem; color: var(--muted); }

.card-section {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 2rem;
  margin: 0 auto 1.5rem;
  max-width: 900px;
  box-shadow: var(--shadow);
}

.card-section h2 { font-size: 1.3rem; font-weight: 700; margin-bottom: .75rem; }
.card-section p { color: var(--muted); }

footer {
  text-align: center;
  padding: 2rem;
  color: var(--muted);
  font-size: .85rem;
  border-top: 1px solid var(--border);
}
"""

_GENERIC_JS = """\
/* Ameer generated page — script.js */
document.addEventListener('DOMContentLoaded', () => {
  console.log('[Ameer] Page loaded.');
});
"""


def _slug_from_command(command: str) -> str:
    """استخلاص slug من نص الأمر.

    يستخدم ما بعد كلمات مثل "عن / حول / about / for" كعنوان للصفحة،
    ثم يحوّله إلى slug آمن للمسارات.
    يعود إلى "project" عند تعذّر الاستخلاص.
    """
    m = re.search(r"(?:عن|حول|about|for)\s+(.+)$", command, flags=re.IGNORECASE)
    raw = m.group(1).strip() if m else ""
    if not raw:
        # fallback: كلمات الأمر بعد كلمات الفعل
        raw = re.sub(r"^(أنشئ|انشئ|إنشاء|build|create|make|اصنع|ابن|ابنِ)\s*", "", command, flags=re.IGNORECASE).strip()
    # تحويل إلى slug: أبجديات لاتينية وعربية وأرقام مفصولة بـ "-"
    slug = re.sub(r"[^\w\u0600-\u06FF]+", "-", raw.lower()).strip("-")
    return slug or "project"


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
        spec = AEX1_INTENT_SPECS.get(intent, {})
        for task in tasks:
            task.setdefault("permission_mode", spec.get("permission_mode", "conversation_only"))
            if spec.get("capability") and not task.get("capability"):
                task["capability"] = spec["capability"]
        return {
            "intent": intent,
            "command": command,
            "tasks": tasks,
            "task_count": len(tasks),
            "permission_mode": spec.get("permission_mode", "conversation_only"),
            "capability": spec.get("capability"),
            "requires_approval": bool(spec.get("requires_approval", False)),
            "execution_intent": intent in AEX1_INTENT_SPECS,
            "decomposed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

    # ── private ───────────────────────────────────────────────────────────────

    def _build_tasks(self, intent: str, command: str) -> List[Dict[str, Any]]:
        if intent == "file_read":
            return self._file_read_tasks(command)
        if intent == "execute_pending_tasks":
            # Load pending tasks from state
            import json
            from pathlib import Path

            state_file = Path(self._root) / ".ameer" / "state.json"
            if not state_file.exists():
                return []

            try:
                with open(state_file, 'r', encoding='utf-8') as f:
                    state_data = json.load(f)

                running_tasks = state_data.get("running_tasks", [])
                tasks_list = []

                for task in running_tasks:
                    if task and isinstance(task, dict):
                        status = task.get("status", "pending").lower()
                        if status in ("pending", "blocked", "running"):
                            task_item = {
                                "id": task.get("id", f"task-{uuid.uuid4()}"),
                                "action": task.get("action", "execute"),
                                "executor": task.get("executor", "shell"),
                                "target": task.get("target", ""),
                                "content": task.get("content", ""),
                                "description": task.get("description", ""),
                                "priority": task.get("priority", "normal"),
                                "status": status,
                            }
                            tasks_list.append(task_item)

                return tasks_list
            except Exception:
                return []
        if intent == "repository_review":
            return self._repository_review_tasks()
        if intent == "code_edit":
            return self._code_edit_tasks(command)
        if intent == "build_website":
            return self._generic_page_tasks(command)
        if intent == "build_store":
            return self._store_tasks(command)
        if intent in {"open_branch", "open_pull_request", "deploy_railway"}:
            return self._external_approval_tasks(intent, command)
        if intent == "build_homepage":
            return self._homepage_tasks()
        if intent == "build_generic":
            return self._generic_page_tasks(command)
        if intent == "run_test":
            return self._run_test_tasks(command)
        # Fallback — return an empty-but-valid placeholder
        return []

    def _file_read_tasks(self, command: str) -> List[Dict[str, Any]]:
        target = _extract_read_target(command)
        if not target:
            return []
        return [
            {
                "id": f"file-read-{uuid.uuid4().hex[:6]}",
                "action": "read",
                "executor": "file",
                "target": target,
                "priority": "high",
                "description": f"قراءة الملف {target}",
                "capability": "file_operations",
                "permission_mode": "read_only",
            }
        ]

    def _repository_review_tasks(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": f"repo-review-{uuid.uuid4().hex[:6]}",
                "action": "run",
                "executor": "shell",
                "command": ["git", "status", "--short"],
                "priority": "high",
                "description": "قراءة حالة المستودع وتحليل التغييرات",
                "capability": "shell_execution",
                "permission_mode": "read_only",
            },
            {
                "id": f"repo-review-diff-{uuid.uuid4().hex[:6]}",
                "action": "run",
                "executor": "shell",
                "command": ["git", "diff", "--stat"],
                "priority": "normal",
                "description": "قراءة ملخص فروق المستودع",
                "capability": "shell_execution",
                "permission_mode": "read_only",
            },
        ]

    def _code_edit_tasks(self, command: str) -> List[Dict[str, Any]]:
        return [{
            "id": f"code-edit-request-{uuid.uuid4().hex[:6]}",
            "action": "write",
            "executor": "file",
            "target": "09_Assets/runtime_workspace/agent_requests/code_edit_request.md",
            "content": f"# AEX-1 Code Edit Request\\n\\n{command.strip()}\\n",
            "priority": "high",
            "description": "تسجيل طلب تعديل الكود داخل مساحة العمل مع تتبع",
            "capability": "file_operations",
            "permission_mode": "tracked_write",
        }]

    def _external_approval_tasks(self, intent: str, command: str) -> List[Dict[str, Any]]:
        target = {
            "open_branch": "github/branch",
            "open_pull_request": "github/pull_request",
            "deploy_railway": "railway/deploy",
        }[intent]
        return [{
            "id": f"{intent}-{uuid.uuid4().hex[:6]}",
            "action": "request",
            "executor": "api",
            "target": target,
            "command": command,
            "priority": "high",
            "description": AEX1_INTENT_SPECS[intent]["description"],
            "capability": "engineering",
            "permission_mode": "external_approval",
            "requires_approval": True,
        }]

    def _run_test_tasks(self, command: str) -> List[Dict[str, Any]]:
        """Generate a shell task to run pytest inside the workspace."""
        # Extract optional path from command (e.g. "run tests in 07_Tests/test_foo.py")
        path_match = re.search(
            r"(?:in|في|of|على)\s+([^\s،؟]+)", command, flags=re.IGNORECASE
        )
        test_path = path_match.group(1).strip() if path_match else "07_Tests/"

        return [
            {
                "id": f"run-test-{uuid.uuid4().hex[:6]}",
                "action": "run",
                "executor": "shell",
                "command": ["python3", "-m", "pytest", test_path, "-v", "--tb=short"],
                "priority": "high",
                "description": f"تشغيل الاختبارات: {test_path}",
                "capability": "shell_execution",
                "permission_mode": "read_only",
            }
        ]

    def _store_tasks(self, command: str) -> List[Dict[str, Any]]:
        slug = _slug_from_command(command)
        prefix = f"{self.RUNTIME_PREFIX}/stores/{slug}"
        title = slug.replace("-", " ").strip() or "store"
        return [
            {
                "id": f"store-html-{slug}", "action": "write", "executor": "file",
                "target": f"{prefix}/index.html",
                "content": _GENERIC_HTML_TPL.format(title=f"متجر {title}", description=f"متجر إلكتروني: {title}"),
                "priority": "high", "description": f"بناء واجهة متجر {title}",
                "capability": "file_operations", "permission_mode": "tracked_write",
            },
            {
                "id": f"store-css-{slug}", "action": "write", "executor": "file",
                "target": f"{prefix}/style.css", "content": _GENERIC_CSS,
                "priority": "high", "description": "تنسيق واجهة المتجر",
                "capability": "file_operations", "permission_mode": "tracked_write",
            },
            {
                "id": f"store-js-{slug}", "action": "write", "executor": "file",
                "target": f"{prefix}/script.js", "content": _GENERIC_JS,
                "priority": "normal", "description": "سلوك واجهة المتجر",
                "capability": "file_operations", "permission_mode": "tracked_write",
            },
        ]

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

    def _generic_page_tasks(self, command: str) -> List[Dict[str, Any]]:
        slug = _slug_from_command(command)
        prefix = f"{self.RUNTIME_PREFIX}/projects/{slug}"
        title = slug.replace("-", " ").strip()
        description_match = re.search(r"(?:عن|حول|about|for)\s+(.+)$", command, flags=re.IGNORECASE)
        description = description_match.group(1).strip() if description_match else title
        html_content = _GENERIC_HTML_TPL.format(title=title, description=description)
        return [
            {
                "id": f"proj-html-{slug}",
                "action": "write",
                "executor": "file",
                "target": f"{prefix}/index.html",
                "content": html_content,
                "priority": "high",
                "description": f"كتابة index.html لمشروع: {title}",
            },
            {
                "id": f"proj-css-{slug}",
                "action": "write",
                "executor": "file",
                "target": f"{prefix}/style.css",
                "content": _GENERIC_CSS,
                "priority": "high",
                "description": f"كتابة style.css لمشروع: {title}",
            },
            {
                "id": f"proj-js-{slug}",
                "action": "write",
                "executor": "file",
                "target": f"{prefix}/script.js",
                "content": _GENERIC_JS,
                "priority": "normal",
                "description": f"كتابة script.js لمشروع: {title}",
            },
        ]
