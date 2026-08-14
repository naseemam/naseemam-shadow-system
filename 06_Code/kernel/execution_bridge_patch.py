from __future__ import annotations

from functools import wraps
from typing import Any, Dict

_INSTALLED = False

_CONTINUATION_MARKERS = (
    "كمل", "أكمل", "اكمل", "خلص", "خلصها", "أنجز", "انجز", "نفذ", "نفّذ",
    "سوي", "سوها", "عدل", "عدّل", "صلح", "أصلح", "راجع", "شيك", "اختبر",
    "continue", "finish", "complete", "fix", "update", "implement",
)

_UI_MARKERS = (
    "الواجهة", "واجهه", "الصفحة", "الصفحه", "الرئيسية", "الرئيسيه", "صندوق الدردشة",
    "الدردشة", "الدردشه", "الأزرار", "الازرار", "homepage", "frontend", "ui", "chat box",
)


def _contains(text: str, terms: tuple[str, ...]) -> bool:
    value = (text or "").strip().lower()
    return any(term.lower() in value for term in terms)


def _enhance_homepage_tasks(result: Dict[str, Any], command: str) -> Dict[str, Any]:
    """Keep the legacy homepage executor useful for the current live UI stage.

    The existing decomposer generates a basic homepage. When the Founder asks for
    the chat box, append a functional chat panel to the generated HTML/CSS/JS so
    execution changes the real UI instead of merely claiming that it did.
    """
    if str(result.get("intent") or "") != "build_homepage":
        return result
    if not _contains(command, ("دردشة", "دردشه", "chat", "صندوق")):
        return result

    tasks = list(result.get("tasks") or [])
    for task in tasks:
        target = str(task.get("target") or "")
        content = str(task.get("content") or "")
        if target.endswith("index.html") and "ameer-chat-panel" not in content:
            panel = """
<section id="chat" class="card-section ameer-chat-panel">
  <h2>تحدث مع أمير</h2>
  <div id="chatMessages" class="chat-messages" aria-live="polite"></div>
  <form id="ameerChatForm" class="chat-form">
    <input id="ameerChatInput" type="text" placeholder="اكتب رسالتك..." autocomplete="off" />
    <button type="submit">إرسال</button>
  </form>
</section>
""".strip()
            content = content.replace("</main>", panel + "\n  </main>")
            content = content.replace('<a href="#contact">تواصل</a>', '<a href="#chat">الدردشة</a>\n      <a href="#contact">تواصل</a>')
            task["content"] = content
        elif target.endswith("style.css") and ".ameer-chat-panel" not in content:
            task["content"] = content + """

/* Ameer chat */
.ameer-chat-panel { scroll-margin-top: 90px; }
.chat-messages { min-height: 180px; max-height: 360px; overflow-y: auto; padding: 1rem; border: 1px solid var(--border); border-radius: var(--radius); background: var(--bg); margin-bottom: 1rem; }
.chat-message { padding: .65rem .8rem; border-radius: 12px; margin: .45rem 0; max-width: 85%; white-space: pre-wrap; }
.chat-message.user { margin-inline-start: auto; background: var(--accent); color: white; }
.chat-message.ameer { margin-inline-end: auto; background: var(--surface); border: 1px solid var(--border); }
.chat-form { display: flex; gap: .6rem; }
.chat-form input { flex: 1; border: 1px solid var(--border); border-radius: 12px; padding: .8rem 1rem; font: inherit; }
.chat-form button { border: 0; border-radius: 12px; padding: .8rem 1.2rem; background: var(--accent); color: white; font: inherit; font-weight: 700; cursor: pointer; }
"""
        elif target.endswith("script.js") and "ameerChatForm" not in content:
            task["content"] = content + """

document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('ameerChatForm');
  const input = document.getElementById('ameerChatInput');
  const messages = document.getElementById('chatMessages');
  if (!form || !input || !messages) return;

  const addMessage = (role, text) => {
    const item = document.createElement('div');
    item.className = `chat-message ${role}`;
    item.textContent = text;
    messages.appendChild(item);
    messages.scrollTop = messages.scrollHeight;
  };

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const query = input.value.trim();
    if (!query) return;
    addMessage('user', query);
    input.value = '';
    try {
      const response = await fetch('/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query })
      });
      const data = await response.json();
      addMessage('ameer', data.reply || data.message || 'تم استلام الطلب.');
    } catch (error) {
      addMessage('ameer', 'تعذر الاتصال بأمير الآن. حاول مرة أخرى.');
    }
  });
});
"""
    result["tasks"] = tasks
    result["task_count"] = len(tasks)
    return result


def install_execution_bridge_patch() -> None:
    """Make natural Founder commands reach the executable kernel lane.

    The conversational brain may understand phrases such as "كمل" or "خلص
    المهمة", but the legacy TaskDecomposer only executes a small set of rigid
    build phrases. This patch remembers the last actionable stage command and
    resolves natural continuation/correction turns against it.
    """
    global _INSTALLED
    if _INSTALLED:
        return

    from kernel.agent_operations import AgentTaskDecomposer

    original_decompose = AgentTaskDecomposer.decompose

    @wraps(original_decompose)
    def decompose(self: AgentTaskDecomposer, command: str) -> Dict[str, Any]:
        result = original_decompose(self, command)
        intent = str(result.get("intent") or "unknown").strip().lower()

        if intent != "unknown":
            self._ameer_last_actionable_command = command
            return _enhance_homepage_tasks(result, command)

        # Natural UI edits should enter the controlled live-repository lane even
        # when they do not use the decomposer's old "build homepage" wording.
        if _contains(command, _CONTINUATION_MARKERS) and _contains(command, _UI_MARKERS):
            synthetic = f"ابن الصفحة الرئيسية الواجهة الحقيقية. {command}"
            bridged = original_decompose(self, synthetic)
            if str(bridged.get("intent") or "unknown") != "unknown":
                self._ameer_last_actionable_command = synthetic
                bridged["execution_bridge"] = "natural_ui_command"
                bridged["original_command"] = command
                return _enhance_homepage_tasks(bridged, command)

        # Short follow-ups inherit the latest actionable stage rather than
        # becoming conversation-only turns.
        if _contains(command, _CONTINUATION_MARKERS):
            previous = str(getattr(self, "_ameer_last_actionable_command", "") or "").strip()
            if previous:
                synthetic = f"{previous}. استمر في نفس المرحلة: {command}"
                bridged = original_decompose(self, synthetic)
                if str(bridged.get("intent") or "unknown") != "unknown":
                    bridged["execution_bridge"] = "stage_continuation"
                    bridged["original_command"] = command
                    return _enhance_homepage_tasks(bridged, synthetic)

        return result

    AgentTaskDecomposer.decompose = decompose
    _INSTALLED = True
