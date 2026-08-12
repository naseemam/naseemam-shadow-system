"""Regex helpers for Arabic normalization and semantic matching."""

from __future__ import annotations

import re


ARABIC_DIACRITICS_RE = re.compile(r"[\u064B-\u0652\u0670\u0610-\u061A\u06D6-\u06ED]")
ARABIC_PUNCTUATION_RE = re.compile(r'[\u061F\u060C\u061B\u066A\u066B\u066C\u066D\u06D4\.,!?؛،؟:؛\-_/\\\[\]\(\){}<>"]')
WHITESPACE_RE = re.compile(r"\s+")


def normalize_arabic_text(text: str) -> str:
    normalized = (text or "").strip().lower()
    if not normalized:
        return ""

    normalized = ARABIC_DIACRITICS_RE.sub("", normalized)
    normalized = normalized.replace("ـ", "")
    normalized = normalized.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").replace("ٱ", "ا")
    normalized = normalized.replace("ى", "ي")
    normalized = normalized.replace("ؤ", "و").replace("ئ", "ي")
    normalized = normalized.replace("ة", "ه")
    normalized = ARABIC_PUNCTUATION_RE.sub(" ", normalized)
    normalized = WHITESPACE_RE.sub(" ", normalized).strip()
    return normalized


def has_any_phrase(text: str, phrases: tuple[str, ...]) -> bool:
    return any(phrase in text for phrase in phrases)
