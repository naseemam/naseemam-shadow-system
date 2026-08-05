"""
test_p06_feedback_learning.py
==============================
P0.6 Feedback & Adaptive Learning Engine — acceptance tests.

Covers:
1.  FeedbackEngine: record with valid types returns an ID
2.  FeedbackEngine: record raises ValueError for empty topic
3.  FeedbackEngine: record raises ValueError for invalid feedback_type
4.  FeedbackEngine: recent() returns recorded entries
5.  FeedbackEngine: by_topic() filters correctly
6.  FeedbackEngine: by_type() filters correctly
7.  FeedbackEngine: snapshot() returns counts by type
8.  FeedbackEngine: persistence across reload
9.  LearningEngine: get_preferences returns defaults on first load
10. LearningEngine: run_learning_cycle applies proactive_frequency → low after 2 negative proactive signals
11. LearningEngine: run_learning_cycle adds topic to disliked_topics after 2 negatives
12. LearningEngine: run_learning_cycle adds topic to proactive_topics after 2 positives
13. LearningEngine: run_learning_cycle updates language from explicit preference signals
14. LearningEngine: reset_preferences restores defaults
15. LearningEngine: build_context_block returns non-empty string with preferences
16. LearningEngine: snapshot returns preferences + log_entries
17. LearningEngine: persistence across reload (preferences survive)
18. ExecutiveKernel: boot reports feedback_engine + learning_engine components
19. ExecutiveKernel: before_request includes learned_preferences + learned_preferences_context
20. ExecutiveKernel: health includes feedback_total + learning_log_entries
21. ameer_server: POST /feedback records feedback
22. ameer_server: POST /feedback returns 422 for invalid feedback_type
23. ameer_server: GET /feedback returns feedback log
24. ameer_server: GET /learning/preferences returns preferences and triggers cycle
25. ameer_server: POST /learning/reset resets preferences
"""

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CODE_ROOT = os.path.join(ROOT, "06_Code")

if CODE_ROOT not in sys.path:
    sys.path.insert(0, CODE_ROOT)


def _load(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# ── FeedbackEngine tests ──────────────────────────────────────────────────────

class FeedbackEngineTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        Path(self._tmp, ".ameer").mkdir(parents=True, exist_ok=True)
        mod = _load("feedback_engine", os.path.join(CODE_ROOT, "kernel", "feedback_engine.py"))
        self.mod = mod
        self.engine = mod.FeedbackEngine(self._tmp)

    def test_record_valid_returns_id(self):
        fid = self.engine.record("positive", "proactive_briefing", comment="مفيد جدًا")
        self.assertIsInstance(fid, str)
        self.assertTrue(len(fid) > 0)

    def test_record_empty_topic_raises(self):
        with self.assertRaises(ValueError):
            self.engine.record("positive", "")

    def test_record_invalid_type_raises(self):
        with self.assertRaises(ValueError):
            self.engine.record("unknown_type", "some_topic")

    def test_recent_returns_entries(self):
        self.engine.record("positive", "topic_a")
        self.engine.record("negative", "topic_b")
        recent = self.engine.recent()
        self.assertEqual(len(recent), 2)

    def test_by_topic_filters(self):
        self.engine.record("positive", "topic_a")
        self.engine.record("negative", "topic_b")
        result = self.engine.by_topic("topic_a")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["topic"], "topic_a")

    def test_by_type_filters(self):
        self.engine.record("positive", "topic_a")
        self.engine.record("negative", "topic_b")
        result = self.engine.by_type("positive")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["feedback_type"], "positive")

    def test_snapshot_counts(self):
        self.engine.record("positive", "t1")
        self.engine.record("positive", "t2")
        self.engine.record("negative", "t3")
        snap = self.engine.snapshot()
        self.assertEqual(snap["total"], 3)
        self.assertEqual(snap["by_type"]["positive"], 2)
        self.assertEqual(snap["by_type"]["negative"], 1)

    def test_persistence_across_reload(self):
        self.engine.record("preference", "tone", comment="أفضّل العربية")
        mod2 = _load("feedback_engine2", os.path.join(CODE_ROOT, "kernel", "feedback_engine.py"))
        engine2 = mod2.FeedbackEngine(self._tmp)
        recent = engine2.recent()
        self.assertEqual(len(recent), 1)
        self.assertEqual(recent[0]["feedback_type"], "preference")


# ── LearningEngine tests ──────────────────────────────────────────────────────

class LearningEngineTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        Path(self._tmp, ".ameer").mkdir(parents=True, exist_ok=True)
        fb_mod = _load("fe_for_le", os.path.join(CODE_ROOT, "kernel", "feedback_engine.py"))
        le_mod = _load("learning_engine", os.path.join(CODE_ROOT, "kernel", "learning_engine.py"))
        self.fb_mod = fb_mod
        self.le_mod = le_mod
        self.feedback = fb_mod.FeedbackEngine(self._tmp)
        self.engine = le_mod.LearningEngine(self._tmp, self.feedback)

    def test_default_preferences(self):
        prefs = self.engine.get_preferences()
        self.assertIn("response_style", prefs)
        self.assertIn("language_preference", prefs)
        self.assertIn("proactive_frequency", prefs)
        self.assertEqual(prefs["proactive_frequency"], "normal")

    def test_cycle_reduces_proactive_after_negatives(self):
        for _ in range(2):
            self.feedback.record("negative", "proactive_briefing")
        result = self.engine.run_learning_cycle()
        prefs = self.engine.get_preferences()
        self.assertEqual(prefs["proactive_frequency"], "low")
        self.assertGreater(result["changes_applied"], 0)

    def test_cycle_adds_disliked_topic(self):
        for _ in range(2):
            self.feedback.record("negative", "weather_updates")
        self.engine.run_learning_cycle()
        prefs = self.engine.get_preferences()
        self.assertIn("weather_updates", prefs["disliked_topics"])

    def test_cycle_adds_proactive_topic(self):
        for _ in range(2):
            self.feedback.record("positive", "project_status")
        self.engine.run_learning_cycle()
        prefs = self.engine.get_preferences()
        self.assertIn("project_status", prefs["proactive_topics"])

    def test_cycle_updates_language_from_preference(self):
        self.feedback.record("preference", "language", comment="I prefer english")
        self.engine.run_learning_cycle()
        prefs = self.engine.get_preferences()
        self.assertEqual(prefs["language_preference"], "english")

    def test_reset_preferences(self):
        for _ in range(2):
            self.feedback.record("negative", "proactive_briefing")
        self.engine.run_learning_cycle()
        self.engine.reset_preferences()
        prefs = self.engine.get_preferences()
        self.assertEqual(prefs["proactive_frequency"], "normal")
        self.assertEqual(prefs["disliked_topics"], [])

    def test_build_context_block_non_empty(self):
        block = self.engine.build_context_block()
        self.assertIsInstance(block, str)
        self.assertTrue(len(block) > 0)

    def test_snapshot_structure(self):
        snap = self.engine.snapshot()
        self.assertIn("preferences", snap)
        self.assertIn("log_entries", snap)
        self.assertIn("last_cycle_at", snap)

    def test_persistence_across_reload(self):
        for _ in range(2):
            self.feedback.record("negative", "proactive_briefing")
        self.engine.run_learning_cycle()
        le_mod2 = _load("learning_engine2", os.path.join(CODE_ROOT, "kernel", "learning_engine.py"))
        engine2 = le_mod2.LearningEngine(self._tmp, self.feedback)
        prefs = engine2.get_preferences()
        self.assertEqual(prefs["proactive_frequency"], "low")


# ── ExecutiveKernel integration tests ────────────────────────────────────────

class KernelFeedbackLearningTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        Path(self._tmp, "04_Memory").mkdir(parents=True, exist_ok=True)
        Path(self._tmp, ".ameer").mkdir(parents=True, exist_ok=True)
        Path(self._tmp, "04_Memory", "Founder.md").write_text("# Founder\nنسيم\n", encoding="utf-8")
        Path(self._tmp, "04_Memory", "Projects.md").write_text("# Projects\n## نظام أمير\n", encoding="utf-8")
        if CODE_ROOT not in sys.path:
            sys.path.insert(0, CODE_ROOT)
        self.mod = _load("executive_kernel_p06", os.path.join(CODE_ROOT, "kernel", "executive_kernel.py"))

    def test_boot_reports_feedback_and_learning(self):
        kernel = self.mod.ExecutiveKernel(self._tmp)
        report = kernel.boot()
        self.assertIn("feedback_engine", report["components"])
        self.assertIn("learning_engine", report["components"])
        self.assertEqual(report["components"]["feedback_engine"], "ok")
        self.assertEqual(report["components"]["learning_engine"], "ok")

    def test_before_request_exposes_learned_preferences(self):
        kernel = self.mod.ExecutiveKernel(self._tmp)
        kernel.boot()
        ctx = kernel.before_request("ما التالي؟")
        self.assertIn("learned_preferences", ctx)
        self.assertIn("learned_preferences_context", ctx)
        self.assertIsInstance(ctx["learned_preferences"], dict)

    def test_health_includes_feedback_and_learning(self):
        kernel = self.mod.ExecutiveKernel(self._tmp)
        kernel.boot()
        h = kernel.health()
        self.assertIn("feedback_total", h)
        self.assertIn("learning_log_entries", h)


# ── Server endpoint tests ─────────────────────────────────────────────────────

class ServerFeedbackLearningTests(unittest.TestCase):
    def setUp(self):
        from fastapi.testclient import TestClient
        import importlib
        # Reload server fresh
        if "ameer_server" in sys.modules:
            del sys.modules["ameer_server"]
        import ameer_server as srv
        self.client = TestClient(srv.app)

    def test_post_feedback_records(self):
        resp = self.client.post("/feedback", json={
            "feedback_type": "positive",
            "topic": "proactive_briefing",
            "comment": "مفيد",
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("id", data)
        self.assertEqual(data["status"], "recorded")

    def test_post_feedback_invalid_type_returns_422(self):
        resp = self.client.post("/feedback", json={
            "feedback_type": "bad_type",
            "topic": "something",
        })
        self.assertEqual(resp.status_code, 422)

    def test_get_feedback_returns_log(self):
        self.client.post("/feedback", json={"feedback_type": "neutral", "topic": "test_topic"})
        resp = self.client.get("/feedback")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("feedback", data)
        self.assertIn("snapshot", data)

    def test_get_learning_preferences(self):
        resp = self.client.get("/learning/preferences")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("preferences", data)
        self.assertIn("learning_snapshot", data)
        self.assertIn("last_cycle", data)

    def test_post_learning_reset(self):
        resp = self.client.post("/learning/reset")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "reset")
        self.assertIn("preferences", data)


if __name__ == "__main__":
    unittest.main()
