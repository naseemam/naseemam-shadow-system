import copy
import re
from typing import Any


class ResponseFormatter:
    _FALLBACK_REPLY = "حاضر، تمت معالجة طلبك. إذا أردت تفاصيل إضافية أخبرني."

    def __init__(self) -> None:
        self._drop_line_patterns = [
            re.compile(r"^\s*(user request|context|system prompt|instruction)\s*[:\-]", re.IGNORECASE),
            re.compile(r"^\s*(طلب المستخدم|السياق|التعليمات)\s*[:\-]", re.IGNORECASE),
            re.compile(r"^\s*(agent|selected_agent|routing|debug|trace|metadata|tool calls?)\s*[:\-]", re.IGNORECASE),
            re.compile(r"^\s*(الوكيل|التوجيه|التصحيح|التتبع|بيانات داخلية|الأدوات)\s*[:\-]", re.IGNORECASE),
        ]
        self._prefix_cleanup_patterns = [
            re.compile(r"^\s*(the answer is|final answer|assistant answer|answer)\s*[:\-]?\s*", re.IGNORECASE),
            re.compile(r"^\s*(الإجابة|الإجابة النهائية|الرد النهائي|الجواب)\s*[:\-]?\s*", re.IGNORECASE),
        ]
        self._internal_phrase_patterns = [
            re.compile(r"\b(user request|context|system prompt|internal prompt|chain of thought)\b", re.IGNORECASE),
            re.compile(r"\b(selected_agent|debug|trace|tool[_\s-]?calls?|execution plan)\b", re.IGNORECASE),
        ]
        self._agent_pattern = re.compile(
            r"\b([a-z]+_agent|identity agent|project agent|research agent|memory agent|greeting agent|recovery agent)\b",
            re.IGNORECASE,
        )
        self._path_pattern = re.compile(
            r"(?<!\w)(?:[A-Za-z]:\\|/)?(?:[\w.-]+/)+[\w.-]+\.(?:py|md|txt|json|js|ts|tsx|css|html|ya?ml|toml|ini|log)\b",
            re.IGNORECASE,
        )

    def _sanitize_line(self, line: str) -> str:
        cleaned = (line or "").strip()
        if not cleaned:
            return ""
        if any(pattern.match(cleaned) for pattern in self._drop_line_patterns):
            return ""
        for pattern in self._prefix_cleanup_patterns:
            cleaned = pattern.sub("", cleaned)
        if any(pattern.search(cleaned) for pattern in self._internal_phrase_patterns):
            return ""

        cleaned = self._path_pattern.sub("", cleaned)
        cleaned = self._agent_pattern.sub("", cleaned)
        cleaned = re.sub(r"\s{2,}", " ", cleaned).strip(" -:|")
        return cleaned.strip()

    def format_text(self, text: Any) -> str:
        if not isinstance(text, str):
            return self._FALLBACK_REPLY

        cleaned = text.replace("\u200f", "")
        cleaned = re.sub(r"```(?:\w+)?", "", cleaned)
        lines = [self._sanitize_line(line) for line in cleaned.splitlines()]
        lines = [line for line in lines if line]
        formatted = " ".join(lines).strip()
        formatted = re.sub(r"\s{2,}", " ", formatted)

        return formatted or self._FALLBACK_REPLY

    def _sanitize_execution_engine(self, execution_engine: Any) -> Any:
        if not isinstance(execution_engine, dict):
            return execution_engine
        sanitized = copy.deepcopy(execution_engine)
        if isinstance(sanitized.get("summary"), str):
            sanitized["summary"] = self.format_text(sanitized["summary"])
        if isinstance(sanitized.get("error"), str):
            sanitized["error"] = self.format_text(sanitized["error"])
        return sanitized

    def format_payload(self, payload: dict) -> dict:
        if not isinstance(payload, dict):
            return {"reply": self._FALLBACK_REPLY}

        formatted = copy.deepcopy(payload)
        formatted["reply"] = self.format_text(formatted.get("reply", ""))
        if isinstance(formatted.get("message"), str):
            formatted["message"] = self.format_text(formatted["message"])
        if isinstance(formatted.get("execution_engine"), dict):
            formatted["execution_engine"] = self._sanitize_execution_engine(formatted["execution_engine"])
        if isinstance(formatted.get("executive_brain"), dict):
            executive = copy.deepcopy(formatted["executive_brain"])
            if isinstance(executive.get("executive_message"), str):
                executive["executive_message"] = self.format_text(executive["executive_message"])
            formatted["executive_brain"] = executive

        formatted.pop("debug_trace", None)
        return formatted
