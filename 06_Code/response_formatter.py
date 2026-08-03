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
        self._filename_pattern = re.compile(
            r"\b[\w.-]+\.(?:py|md|txt|json|js|ts|tsx|css|html|ya?ml|toml|ini|log)\b",
            re.IGNORECASE,
        )
        self._internal_word_pattern = re.compile(
            r"\b(debug|trace|routing|selected_agent|agent|prompt|instruction|execution|tool calls?|metadata)\b",
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
        cleaned = self._filename_pattern.sub("", cleaned)
        cleaned = self._agent_pattern.sub("", cleaned)
        cleaned = self._internal_word_pattern.sub("", cleaned)
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

    def format_payload(self, payload: dict) -> dict:
        if not isinstance(payload, dict):
            return {"reply": self._FALLBACK_REPLY}

        response_data = self._extract_response_data(payload)
        composed = self._compose_from_structured_data(response_data)
        safe_reply = self.format_text(composed or payload.get("reply", "") or payload.get("message", ""))
        return {
            "reply": safe_reply,
            "message": safe_reply,
            "assistant": "أمير",
        }

    def _extract_response_data(self, payload: dict) -> dict:
        if not isinstance(payload, dict):
            return {}
        candidates = [
            payload.get("agent_brain_payload"),
            payload.get("agent_result"),
        ]
        for candidate in candidates:
            if isinstance(candidate, dict):
                response_data = candidate.get("response_data", {})
                if isinstance(response_data, dict) and response_data:
                    return response_data
        return {}

    def _compose_from_structured_data(self, response_data: dict) -> str:
        if not isinstance(response_data, dict):
            return ""
        intent = str(response_data.get("intent", "")).strip().lower()
        facts = response_data.get("facts", {})
        if not isinstance(facts, dict):
            facts = {}

        if intent == "identity":
            subject = str(facts.get("subject", "")).strip().lower()
            if subject == "founder":
                return "نسيم هي المؤسسة وصاحبة القرار النهائي في مشروع أمير."
            return "أنا أمير، شريكك التنفيذي الذكي لدعم إدارة المشاريع وتنظيم المعرفة واتخاذ القرارات."

        if intent == "greeting":
            mode = str(facts.get("mode", "")).strip().lower()
            if mode == "name_call":
                return "نعم، أنا معك. كيف أساعدك الآن؟"
            return "مرحبًا نسيم، أنا حاضر. كيف تحبين أن نبدأ؟"

        if intent in {"project", "research", "memory"}:
            status = str(facts.get("status", "")).strip().lower()
            excerpt = str(facts.get("top_excerpt", "")).strip()
            if status in {"found", "follow_up", "plan_shifted"} and excerpt:
                return excerpt[:260]
            if intent == "memory":
                return "راجعت الذاكرة المتاحة، وإذا أردت أستطيع تضييق البحث على نقطة محددة."
            if intent == "project":
                return "راجعت سياق المشروع، ويمكنني تحويله إلى خطوات تنفيذية واضحة حسب أولوياتك."
            return "راجعت السياق المتاح، ويمكنني تقديم إجابة أدق إذا حددت الهدف بشكل أوضح."

        if intent == "recovery":
            return "واجهت تعارضًا داخليًا بسيطًا وتم تفعيل مسار آمن للاستمرار. أقدر أكمل معك بشكل طبيعي."

        return ""
