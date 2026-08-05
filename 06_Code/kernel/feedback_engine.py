"""
feedback_engine.py
==================
Feedback Engine — محرك التغذية الراجعة لنظام أمير.

يسجّل ردود فعل المؤسسة على استجابات أمير واقتراحاته الاستباقية،
ويحتفظ بتاريخ التغذية الراجعة بشكل دائم.

Feedback types:
  positive  — رد إيجابي (الاقتراح كان مفيدًا)
  negative  — رد سلبي (الاقتراح غير مناسب أو مزعج)
  neutral   — ملاحظة محايدة أو تصحيح
  preference — تعبير عن تفضيل مباشر
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


VALID_TYPES = {"positive", "negative", "neutral", "preference"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class FeedbackEngine:
    """
    يسجّل ويسترجع تغذية راجعة المؤسسة حول أداء أمير.

    المسؤوليات:
    1. قبول إشارات التغذية الراجعة وتخزينها
    2. توفير تاريخ التغذية الراجعة الأخيرة
    3. تجميع التغذية الراجعة بحسب النوع والموضوع
    """

    _FILENAME = "feedback_log.json"

    def __init__(self, workspace_root: str | Path) -> None:
        self._root = Path(workspace_root).resolve()
        self._path = self._root / ".ameer" / self._FILENAME
        self._records: List[Dict[str, Any]] = self._load()

    # ── Persistence ───────────────────────────────────────────────────────────

    def _load(self) -> List[Dict[str, Any]]:
        if self._path.exists():
            try:
                data = json.loads(self._path.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    return data
            except Exception:
                pass
        return []

    def _persist(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(self._records, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    # ── Public API ────────────────────────────────────────────────────────────

    def record(
        self,
        feedback_type: str,
        topic: str,
        comment: str = "",
        context: Optional[Dict[str, Any]] = None,
        source: str = "founder",
    ) -> str:
        """
        تسجيل وحدة تغذية راجعة.

        Parameters
        ----------
        feedback_type : str
            نوع التغذية الراجعة: positive | negative | neutral | preference
        topic : str
            الموضوع أو الفئة (مثلاً: "proactive_briefing"، "memory_suggestion"، "tone")
        comment : str
            ملاحظة نصية اختيارية
        context : dict | None
            سياق إضافي (مثلاً: المحادثة أو القرار المرتبط)
        source : str
            مصدر التغذية (افتراضي: "founder")

        Returns
        -------
        str
            معرّف التغذية الراجعة
        """
        if not topic or not topic.strip():
            raise ValueError("topic must not be empty")
        if feedback_type not in VALID_TYPES:
            raise ValueError(f"feedback_type must be one of {sorted(VALID_TYPES)}")

        record: Dict[str, Any] = {
            "id": str(uuid.uuid4()),
            "feedback_type": feedback_type,
            "topic": topic.strip(),
            "comment": comment.strip(),
            "context": context or {},
            "source": source,
            "recorded_at": _now_iso(),
        }
        self._records.append(record)
        self._persist()
        return record["id"]

    def recent(self, limit: int = 20) -> List[Dict[str, Any]]:
        """أحدث وحدات التغذية الراجعة."""
        return list(self._records[-limit:])

    def by_topic(self, topic: str) -> List[Dict[str, Any]]:
        """كل التغذية الراجعة المرتبطة بموضوع معيّن."""
        return [r for r in self._records if r.get("topic") == topic]

    def by_type(self, feedback_type: str) -> List[Dict[str, Any]]:
        """كل التغذية الراجعة من نوع معيّن."""
        return [r for r in self._records if r.get("feedback_type") == feedback_type]

    def snapshot(self) -> Dict[str, Any]:
        """ملخص إحصائي لحالة التغذية الراجعة."""
        total = len(self._records)
        counts: Dict[str, int] = {}
        for r in self._records:
            ft = r.get("feedback_type", "unknown")
            counts[ft] = counts.get(ft, 0) + 1
        topics: List[str] = list({r.get("topic", "") for r in self._records})
        return {
            "total": total,
            "by_type": counts,
            "topics": topics,
            "last_recorded_at": self._records[-1].get("recorded_at") if self._records else None,
        }
