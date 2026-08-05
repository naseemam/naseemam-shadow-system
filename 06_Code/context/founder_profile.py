"""
founder_profile.py
==================
Founder Active Profile — ذاكرة المؤسسة دائمًا حاضرة.

يُحمِّل ملفات 04_Memory/ تلقائيًا عند الـ startup
ويُبني سياقًا مضغوطًا يُدرج في كل reasoning cycle.
أمير لا ينتظر حتى تسأله المؤسسة — يعرفها دائمًا.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Optional


# الملفات الجوهرية لهوية المؤسسة — بالأولوية
_PRIORITY_FILES = [
    "Founder.md",
    "Goals.md",
    "Projects.md",
    "Finance.md",
    "Preferences.md",
    "Routine.md",
    "Health.md",
    "Relationships.md",
]

_MAX_CHARS_PER_FILE = 800
_MAX_TOTAL_CHARS = 3_000


class FounderProfile:
    """
    يُحمِّل ويُلخِّص ذاكرة المؤسسة.
    يوفر سياقًا جاهزًا لإدراجه في system prompt.
    """

    def __init__(self, workspace_root: str | Path) -> None:
        self._memory_dir = Path(workspace_root).resolve() / "04_Memory"
        self._sections: Dict[str, str] = {}
        self._loaded = False

    def load(self) -> None:
        """تحميل ملفات الذاكرة."""
        sections: Dict[str, str] = {}
        # Priority files first
        for fname in _PRIORITY_FILES:
            fpath = self._memory_dir / fname
            if fpath.exists():
                try:
                    text = fpath.read_text(encoding="utf-8").strip()
                    # Remove Arabic support boilerplate
                    text = _strip_boilerplate(text)
                    if text:
                        sections[fname] = text[:_MAX_CHARS_PER_FILE]
                except Exception:
                    pass
        # Remaining .md files
        try:
            for fpath in sorted(self._memory_dir.glob("*.md")):
                fname = fpath.name
                if fname not in sections:
                    try:
                        text = fpath.read_text(encoding="utf-8").strip()
                        text = _strip_boilerplate(text)
                        if text:
                            sections[fname] = text[:_MAX_CHARS_PER_FILE]
                    except Exception:
                        pass
        except Exception:
            pass
        self._sections = sections
        self._loaded = True

    def reload(self) -> None:
        self._loaded = False
        self.load()

    def build_context_block(self) -> str:
        """
        يبني نصًا مضغوطًا لإدراجه في system prompt.
        يشمل هوية المؤسسة وأهدافها ومشاريعها.
        """
        if not self._loaded:
            self.load()

        if not self._sections:
            return ""

        lines: List[str] = ["[ معلومات المؤسسة (نسيم):"]
        total = 0
        for fname in _PRIORITY_FILES:
            if fname not in self._sections:
                continue
            content = self._sections[fname]
            excerpt = _extract_key_lines(content, max_chars=400)
            if excerpt:
                label = fname.replace(".md", "")
                block = f"  {label}: {excerpt}"
                total += len(block)
                if total > _MAX_TOTAL_CHARS:
                    break
                lines.append(block)

        if len(lines) == 1:
            return ""

        lines.append("]")
        return "\n".join(lines)

    def get_section(self, filename: str) -> Optional[str]:
        if not self._loaded:
            self.load()
        return self._sections.get(filename)

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def sections(self) -> Dict[str, str]:
        if not self._loaded:
            self.load()
        return dict(self._sections)


def _strip_boilerplate(text: str) -> str:
    """يحذف النص المعياري المتكرر في نهاية كل ملف."""
    boilerplate_markers = [
        "## Arabic Support",
        "## Arabic Support / دعم اللغة العربية",
    ]
    for marker in boilerplate_markers:
        idx = text.find(marker)
        if idx != -1:
            text = text[:idx].strip()
    return text


def _extract_key_lines(text: str, max_chars: int = 400) -> str:
    """يستخرج الأسطر الجوهرية من نص الملف."""
    lines: List[str] = []
    total = 0
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        # Skip headers and dividers
        if line.startswith("#") or line.startswith("---"):
            continue
        lines.append(line)
        total += len(line)
        if total >= max_chars:
            break
    return " | ".join(lines) if lines else ""
