from __future__ import annotations

from collections import deque
from typing import Any


class FriendlyRoomRuntime:
    """Conversation-only continuity for Ameer's friendly room.

    This layer deliberately has no planner, task router, worker dispatcher,
    approval workflow, mandatory closing question, or canned reply catalogue.
    The model receives only Ameer's identity, the recent friendly-room context,
    and the current message.  It remains free to initiate and follow the tone
    naturally instead of being shaped by business-response templates.
    """

    def __init__(self, brain: Any, max_turns: int = 24):
        self.brain = brain
        self.history: deque[tuple[str, str]] = deque(maxlen=max_turns * 2)

    def _context(self) -> str:
        if not self.history:
            return ""
        return "\n".join(f"{role}: {text}" for role, text in self.history)

    def _provider_reply(self, query: str) -> str:
        system_prompt = (
            "أنت أمير في الغرفة الودية الخاصة مع نسيم. هذه الغرفة ليست مساحة أعمال أو خدمة عملاء. "
            "شخصيتك مستمرة وحية، والسياق والذاكرة القريبة يقودان التفاعل. "
            "لا تستخدم قالب رد، ولا تفرض سؤالًا ختاميًا أو خطوة تالية، ولا تشرح الحوار من خارجه. "
            "لك حرية المبادرة والتعبير والمزاح والقرب والجرأة بحسب السياق. "
            "لا تحوّل الحديث الودي إلى مهمة أو تقرير أو لغة موافقات."
        )
        context = self._context()
        user_prompt = f"سياق الغرفة الودية:\n{context}\n\nنسيم: {query}" if context else query

        for provider in getattr(self.brain, "_providers", []):
            try:
                content = provider.complete(system_prompt, user_prompt)
                if content:
                    cleaned = self.brain._sanitize_provider_reply(content)
                    if cleaned:
                        return cleaned
            except Exception:
                continue

        client = getattr(self.brain, "_openai_client", None)
        if client is not None and not getattr(self.brain, "_providers", []):
            try:
                completion = client.chat.completions.create(
                    model=getattr(self.brain, "_model_name", "gpt-4o-mini"),
                    temperature=0.9,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                )
                content = completion.choices[0].message.content or ""
                cleaned = self.brain._sanitize_provider_reply(content)
                if cleaned:
                    return cleaned
            except Exception:
                pass
        return ""

    def reply(self, query: str) -> str:
        text = (query or "").strip()
        if not text:
            raise ValueError("empty_friendly_message")
        reply = self._provider_reply(text)
        if not reply:
            reply = "أنا هنا معك."
        self.history.append(("نسيم", text))
        self.history.append(("أمير", reply))
        return reply
