"""
session_context.py
==================
Session Context Manager — محادثة متراكمة لا stateless.

يحتفظ بتاريخ المحادثة الحالية كـ rolling window
ويُمرّره إلى كل reasoning cycle.
"""

from __future__ import annotations

from collections import deque
from typing import Dict, List


_MAX_TURNS = 20          # أقصى عدد أدوار تُحفَظ
_MAX_CHARS = 8_000       # حد الأحرف لتجنب تجاوز tokens


class SessionContext:
    """
    يحتفظ بتاريخ المحادثة كـ rolling window.
    كل turn = {"role": "user"|"assistant", "content": str}
    """

    def __init__(self, max_turns: int = _MAX_TURNS) -> None:
        self._history: deque[Dict[str, str]] = deque(maxlen=max_turns)

    def add_user_message(self, content: str) -> None:
        self._history.append({"role": "user", "content": (content or "").strip()})

    def add_assistant_message(self, content: str) -> None:
        self._history.append({"role": "assistant", "content": (content or "").strip()})

    def get_messages(self) -> List[Dict[str, str]]:
        """قائمة الرسائل بالترتيب الزمني."""
        return list(self._history)

    def get_trimmed_messages(self, max_chars: int = _MAX_CHARS) -> List[Dict[str, str]]:
        """
        يُعيد تاريخ المحادثة مع ضمان عدم تجاوز max_chars.
        يحذف الرسائل الأقدم أولاً.
        """
        messages = list(self._history)
        total = sum(len(m["content"]) for m in messages)
        while messages and total > max_chars:
            removed = messages.pop(0)
            total -= len(removed["content"])
        return messages

    def build_context_block(self, max_chars: int = _MAX_CHARS) -> str:
        """
        يبني نصًا مضغوطًا من تاريخ المحادثة
        لإدراجه في system prompt.
        """
        messages = self.get_trimmed_messages(max_chars)
        if not messages:
            return ""
        lines: List[str] = []
        for msg in messages[:-1]:  # نستثني آخر رسالة (الطلب الحالي)
            role = "نسيم" if msg["role"] == "user" else "أمير"
            lines.append(f"{role}: {msg['content'][:200]}")
        if not lines:
            return ""
        return "[ سياق المحادثة:\n" + "\n".join(lines) + "\n]"

    def is_follow_up(self) -> bool:
        """هل هذا متابعة لمحادثة سابقة؟"""
        return len(self._history) > 1

    def clear(self) -> None:
        self._history.clear()

    def __len__(self) -> int:
        return len(self._history)
