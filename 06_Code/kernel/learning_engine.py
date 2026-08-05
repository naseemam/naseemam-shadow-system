"""
learning_engine.py
==================
Learning Engine — محرك التعلم التكيفي الآمن لنظام أمير.

يحلّل التغذية الراجعة المخزّنة ويستخلص تفضيلات المؤسسة.
لا يُغيّر هوية أمير أو قيمه الأساسية بدون موافقة المؤسسة الصريحة.

Learning modes (per Learning_System.md):
  adaptive    — تحسين الردود بناءً على أنماط التفاعل
  preference  — تعلّم تفضيلات التواصل والأسلوب
  decision    — تسجيل خبرة القرارات ونتائجها لإثراء التوجيه
"""

from __future__ import annotations

import json
import copy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from kernel.feedback_engine import FeedbackEngine


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ── Default preference schema ─────────────────────────────────────────────────

_DEFAULT_PREFERENCES: Dict[str, Any] = {
    "response_style": "detailed",        # detailed | concise
    "language_preference": "arabic",     # arabic | english | mixed
    "proactive_frequency": "normal",     # low | normal | high
    "proactive_topics": [],              # topics the founder finds useful
    "disliked_topics": [],               # topics the founder found intrusive
    "tone": "partner",                   # formal | partner | casual
    "updated_at": None,
    "version": 1,
}

# Minimum feedback signals required before updating a preference
_MIN_SIGNALS = 2


class LearningEngine:
    """
    يحلّل التغذية الراجعة ويُحدّث تفضيلات المؤسسة بطريقة آمنة.

    المبادئ:
    - لا يُغيّر هوية أمير أو دستوره بدون موافقة صريحة.
    - التعلم مقيّد بتفضيلات التواصل وأنماط الاستجابة فقط.
    - كل تغيير يُسجَّل في سجل التعلم للمراجعة.
    - المؤسسة تستطيع إعادة الضبط في أي وقت.
    """

    _PREFS_FILE = "learned_preferences.json"
    _LOG_FILE = "learning_log.json"

    def __init__(self, workspace_root: str | Path, feedback: Optional[FeedbackEngine] = None) -> None:
        self._root = Path(workspace_root).resolve()
        self._prefs_path = self._root / ".ameer" / self._PREFS_FILE
        self._log_path = self._root / ".ameer" / self._LOG_FILE
        self._feedback = feedback or FeedbackEngine(workspace_root)
        self._preferences: Dict[str, Any] = self._load_preferences()
        self._log: List[Dict[str, Any]] = self._load_log()

    # ── Persistence ───────────────────────────────────────────────────────────

    def _load_preferences(self) -> Dict[str, Any]:
        if self._prefs_path.exists():
            try:
                data = json.loads(self._prefs_path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    merged = copy.deepcopy(_DEFAULT_PREFERENCES)
                    merged.update(data)
                    return merged
            except Exception:
                pass
        prefs = copy.deepcopy(_DEFAULT_PREFERENCES)
        self._save_preferences(prefs)
        return prefs

    def _save_preferences(self, prefs: Optional[Dict[str, Any]] = None) -> None:
        if prefs is not None:
            self._preferences = prefs
        self._preferences["updated_at"] = _now_iso()
        self._prefs_path.parent.mkdir(parents=True, exist_ok=True)
        self._prefs_path.write_text(
            json.dumps(self._preferences, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _load_log(self) -> List[Dict[str, Any]]:
        if self._log_path.exists():
            try:
                data = json.loads(self._log_path.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    return data
            except Exception:
                pass
        return []

    def _append_log(self, entry: Dict[str, Any]) -> None:
        self._log.append(entry)
        self._log_path.parent.mkdir(parents=True, exist_ok=True)
        self._log_path.write_text(
            json.dumps(self._log, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    # ── Core learning loop ────────────────────────────────────────────────────

    def run_learning_cycle(self) -> Dict[str, Any]:
        """
        تحليل التغذية الراجعة وتحديث التفضيلات إذا توفّرت إشارات كافية.
        يُعيد ملخص التغييرات المُطبَّقة.
        """
        changes: List[str] = []
        feedback_snapshot = self._feedback.snapshot()

        # ── Preference: proactive_frequency ──────────────────────────────────
        briefing_positive = len(self._feedback.by_type("positive"))
        briefing_negative = len([
            r for r in self._feedback.by_type("negative")
            if "proactive" in r.get("topic", "")
        ])
        if briefing_negative >= _MIN_SIGNALS and self._preferences["proactive_frequency"] != "low":
            self._preferences["proactive_frequency"] = "low"
            changes.append("proactive_frequency → low (repeated negative feedback on proactive topics)")
        elif briefing_positive >= _MIN_SIGNALS and briefing_negative == 0 \
                and self._preferences["proactive_frequency"] == "low":
            self._preferences["proactive_frequency"] = "normal"
            changes.append("proactive_frequency → normal (consistent positive feedback)")

        # ── Preference: disliked_topics ───────────────────────────────────────
        neg_records = self._feedback.by_type("negative")
        for rec in neg_records:
            topic = rec.get("topic", "")
            if topic and topic not in self._preferences["disliked_topics"]:
                topic_neg_count = sum(
                    1 for r in neg_records if r.get("topic") == topic
                )
                if topic_neg_count >= _MIN_SIGNALS:
                    self._preferences["disliked_topics"].append(topic)
                    changes.append(f"added '{topic}' to disliked_topics")

        # ── Preference: proactive_topics ──────────────────────────────────────
        pos_records = self._feedback.by_type("positive")
        for rec in pos_records:
            topic = rec.get("topic", "")
            if topic and topic not in self._preferences["proactive_topics"]:
                topic_pos_count = sum(
                    1 for r in pos_records if r.get("topic") == topic
                )
                if topic_pos_count >= _MIN_SIGNALS:
                    self._preferences["proactive_topics"].append(topic)
                    changes.append(f"added '{topic}' to proactive_topics")

        # ── Preference: language from explicit preference signals ─────────────
        pref_records = self._feedback.by_type("preference")
        for rec in pref_records:
            comment_lower = rec.get("comment", "").lower()
            if "arabic" in comment_lower or "عربي" in rec.get("comment", ""):
                if self._preferences["language_preference"] != "arabic":
                    self._preferences["language_preference"] = "arabic"
                    changes.append("language_preference → arabic (explicit preference signal)")
            elif "english" in comment_lower or "إنجليزي" in rec.get("comment", ""):
                if self._preferences["language_preference"] != "english":
                    self._preferences["language_preference"] = "english"
                    changes.append("language_preference → english (explicit preference signal)")

        # ── Persist if anything changed ───────────────────────────────────────
        if changes:
            self._save_preferences()
            self._append_log({
                "cycle_at": _now_iso(),
                "changes": changes,
                "feedback_snapshot": feedback_snapshot,
            })

        return {
            "cycle_at": _now_iso(),
            "changes_applied": len(changes),
            "changes": changes,
            "current_preferences": dict(self._preferences),
        }

    # ── Preferences access ────────────────────────────────────────────────────

    def get_preferences(self) -> Dict[str, Any]:
        """يُعيد التفضيلات الحالية المُتعلَّمة."""
        return dict(self._preferences)

    def reset_preferences(self) -> None:
        """إعادة ضبط التفضيلات إلى الإعدادات الافتراضية (بموافقة المؤسسة)."""
        prefs = copy.deepcopy(_DEFAULT_PREFERENCES)
        self._save_preferences(prefs)
        self._append_log({
            "cycle_at": _now_iso(),
            "changes": ["preferences reset to defaults"],
            "feedback_snapshot": self._feedback.snapshot(),
        })

    def build_context_block(self) -> str:
        """يُنتج نص سياق التفضيلات لإدراجه في prompt أمير."""
        parts: List[str] = []
        prefs = self._preferences
        if prefs.get("language_preference"):
            parts.append(f"لغة التفاعل المُفضَّلة: {prefs['language_preference']}")
        if prefs.get("proactive_frequency"):
            parts.append(f"تكرار الاقتراحات الاستباقية: {prefs['proactive_frequency']}")
        if prefs.get("disliked_topics"):
            parts.append("مواضيع غير مرغوب فيها: " + "، ".join(prefs["disliked_topics"][:5]))
        if prefs.get("proactive_topics"):
            parts.append("مواضيع ذات قيمة مرتفعة: " + "، ".join(prefs["proactive_topics"][:5]))
        return " | ".join(parts) if parts else ""

    def snapshot(self) -> Dict[str, Any]:
        """ملخص حالة محرك التعلم."""
        return {
            "preferences": dict(self._preferences),
            "log_entries": len(self._log),
            "last_cycle_at": self._log[-1].get("cycle_at") if self._log else None,
        }
