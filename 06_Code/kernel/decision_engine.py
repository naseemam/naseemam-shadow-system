"""
decision_engine.py
==================
Executive Decision Engine — سجل القرارات الدائم.

كل قرار مهم يتخذه أمير أو تتخذه المؤسسة يُسجَّل هنا مع:
- السبب (reason)
- النتيجة المتوقعة (expected_outcome)
- النتيجة الفعلية عند التحديث (actual_outcome)
- الحالة: pending / accepted / rejected / completed

يُخزَّن في .ameer/decisions.json لضمان البقاء عبر الجلسات.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


_DECISIONS_FILENAME = "decisions.json"
_MAX_RECENT = 50  # نبقي آخر 50 قراراً في الذاكرة العاملة


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class DecisionEngine:
    """
    محرك تسجيل القرارات التنفيذية.

    واجهة الاستخدام:
    ----------------
    engine = DecisionEngine(workspace_root)
    decision_id = engine.record(
        title="إطلاق موقع حلم الندى",
        reason="طلبت المؤسسة إطلاق الموقع في موعد العرض",
        category="project",
    )
    engine.update_outcome(decision_id, "تم الإطلاق بنجاح")

    كل قرار له بنية ثابتة:
    {
        "id": "<uuid>",
        "title": "...",
        "reason": "...",
        "category": "project|task|approval|system|other",
        "status": "pending|accepted|rejected|completed",
        "expected_outcome": "...",
        "actual_outcome": "...",
        "recorded_at": "<iso>",
        "resolved_at": "<iso|null>",
    }
    """

    VALID_CATEGORIES = {"project", "task", "approval", "system", "other"}
    VALID_STATUSES = {"pending", "accepted", "rejected", "completed"}

    def __init__(self, workspace_root: str | Path) -> None:
        self._root = Path(workspace_root).resolve()
        self._path = self._root / ".ameer" / _DECISIONS_FILENAME
        self._decisions: List[Dict[str, Any]] = []
        self._load()

    # ── Persistence ───────────────────────────────────────────────────────────

    def _load(self) -> None:
        if self._path.exists():
            try:
                raw = self._path.read_text(encoding="utf-8")
                loaded = json.loads(raw)
                if isinstance(loaded, list):
                    self._decisions = loaded
                    return
            except Exception:
                pass
        self._decisions = []

    def _save(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(
                json.dumps(self._decisions, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
            pass  # ديمومة اختيارية — لا نُفشل الطلب بسببها

    # ── Core API ──────────────────────────────────────────────────────────────

    def record(
        self,
        title: str,
        reason: str,
        category: str = "other",
        expected_outcome: str = "",
        status: str = "pending",
    ) -> str:
        """
        يُسجّل قراراً جديداً ويُعيد معرّفه.

        :param title: عنوان القرار (مختصر)
        :param reason: السبب أو المسوّغ
        :param category: project | task | approval | system | other
        :param expected_outcome: النتيجة المتوقعة (اختياري)
        :param status: pending | accepted | rejected | completed
        :returns: decision_id (UUID string)
        """
        if not title or not title.strip():
            raise ValueError("title is required")
        if not reason or not reason.strip():
            raise ValueError("reason is required")
        if category not in self.VALID_CATEGORIES:
            category = "other"
        if status not in self.VALID_STATUSES:
            status = "pending"

        decision: Dict[str, Any] = {
            "id": str(uuid.uuid4()),
            "title": title.strip(),
            "reason": reason.strip(),
            "category": category,
            "status": status,
            "expected_outcome": (expected_outcome or "").strip(),
            "actual_outcome": "",
            "recorded_at": _now_iso(),
            "resolved_at": None,
        }
        self._decisions.append(decision)
        # Keep within memory cap (drop oldest)
        if len(self._decisions) > _MAX_RECENT:
            self._decisions = self._decisions[-_MAX_RECENT:]
        self._save()
        return decision["id"]

    def update_outcome(
        self,
        decision_id: str,
        actual_outcome: str,
        status: str = "completed",
    ) -> bool:
        """
        يُحدّث النتيجة الفعلية لقرار مسجَّل.

        :returns: True إذا وُجد القرار وحُدِّث، False إذا لم يُوجد.
        """
        if status not in self.VALID_STATUSES:
            status = "completed"
        for decision in self._decisions:
            if decision["id"] == decision_id:
                decision["actual_outcome"] = (actual_outcome or "").strip()
                decision["status"] = status
                decision["resolved_at"] = _now_iso()
                self._save()
                return True
        return False

    def get(self, decision_id: str) -> Optional[Dict[str, Any]]:
        """يُعيد قراراً بمعرّفه، أو None إن لم يوجد."""
        for decision in self._decisions:
            if decision["id"] == decision_id:
                return dict(decision)
        return None

    def recent(self, limit: int = 10) -> List[Dict[str, Any]]:
        """يُعيد آخر N قراراً (الأحدث أولاً)."""
        return [dict(d) for d in reversed(self._decisions[-limit:])]

    def pending(self) -> List[Dict[str, Any]]:
        """يُعيد القرارات التي لا تزال في حالة pending."""
        return [dict(d) for d in self._decisions if d.get("status") == "pending"]

    def snapshot(self) -> Dict[str, Any]:
        """ملخص حالة محرك القرارات."""
        return {
            "total": len(self._decisions),
            "pending": len(self.pending()),
            "recent": self.recent(5),
        }
