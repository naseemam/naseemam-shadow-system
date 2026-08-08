import importlib.util
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from urllib import request as urllib_request


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CODE_ROOT = os.path.join(ROOT, "06_Code")


def _load(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _post_json(url: str, payload: dict) -> dict:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib_request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    with urllib_request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


class PersistentMemoryTests(unittest.TestCase):
    def test_memory_survives_reload(self):
        mod = _load("executive_conversation", os.path.join(CODE_ROOT, "executive_conversation.py"))
        with tempfile.TemporaryDirectory() as tmp:
            mem1 = mod.PersistentConversationMemory(tmp)
            plan = mod.ConversationPlannerState(
                executive_objective="متابعة مشروع أمير",
                founder_objective="حسم أولوية التنفيذ",
                current_project_objective="مشروع أمير",
                detected_risks=["موافقة معلقة"],
                missing_information=[],
                next_executive_action="أغلقي طلب الموافقة أولًا.",
            )
            mem1.update_after_reply("ما الأولوية الآن؟", "أقترح إغلاق الموافقة أولًا.", plan)
            mem2 = mod.PersistentConversationMemory(tmp)
            snapshot = mem2.snapshot()
            self.assertTrue(snapshot["recurring_topics"])
            self.assertTrue(snapshot["executive_commitments"])


class KernelConversationMemoryTests(unittest.TestCase):
    def test_before_request_exposes_persistent_memory(self):
        if CODE_ROOT not in sys.path:
            sys.path.insert(0, CODE_ROOT)
        mod = _load("executive_kernel", os.path.join(CODE_ROOT, "kernel", "executive_kernel.py"))
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "04_Memory").mkdir(parents=True, exist_ok=True)
            Path(tmp, ".ameer").mkdir(parents=True, exist_ok=True)
            Path(tmp, "04_Memory", "Founder.md").write_text("# Founder\nنسيم\n", encoding="utf-8")
            Path(tmp, "04_Memory", "Projects.md").write_text("# Projects\n## نظام أمير\n", encoding="utf-8")
            kernel = mod.ExecutiveKernel(tmp)
            kernel.boot()
            ctx = kernel.before_request("ما التالي؟")
            self.assertIn("persistent_conversation_memory", ctx)
            self.assertIn("persistent_memory_context", ctx)


class LivePipelineExecutionTests(unittest.TestCase):
    def test_debug_trace_shows_conversation_engine_on_real_ask(self):
        port = _find_free_port()
        env = {**os.environ, "AMEER_PORT": str(port), "AMEER_DEBUG": "1"}
        proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "ameer_server:app", "--host", "127.0.0.1", "--port", str(port)],
            cwd=ROOT,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        try:
            deadline = time.time() + 20
            while time.time() < deadline:
                try:
                    data = _post_json(f"http://127.0.0.1:{port}/ask", {"query": "أمير", "max_results": 3})
                    self.assertIn("reply", data)
                    break
                except Exception:
                    time.sleep(0.4)
            else:
                self.fail("server did not respond in time")

            out, err = proc.communicate(timeout=1)
        except subprocess.TimeoutExpired:
            proc.terminate()
            out, err = proc.communicate(timeout=6)
        finally:
            if proc.poll() is None:
                proc.terminate()
                proc.wait(timeout=6)

        logs = (out or b"").decode("utf-8", errors="replace") + (err or b"").decode("utf-8", errors="replace")
        self.assertIn("executive_conversation_engine", logs)


class ConversationalLeakRegressionTests(unittest.TestCase):
    """
    Regression: conversational messages must not trigger the open-tasks warning
    even when running_tasks contains stale pending entries.

    Production issue: /ask with a conversational query returned
    "لفت انتباهي أن مهام مفتوحة تشغل موارد..." instead of a conversational reply.
    """

    def _load_ece(self):
        mod = _load("executive_conversation", os.path.join(CODE_ROOT, "executive_conversation.py"))
        return mod

    def _make_reasoning_output(self, request_type: str) -> dict:
        return {"reasoning": {"request_type": request_type, "guardian_status": "pass"}}

    def _stalled_tasks(self) -> list:
        return [{"id": "t1", "title": "مهمة قديمة", "status": "pending"}]

    def test_conversational_question_with_stalled_tasks_does_not_leak_task_warning(self):
        """request_type=question + stalled tasks → AI reply must pass through unchanged."""
        mod = self._load_ece()
        with tempfile.TemporaryDirectory() as tmp:
            ece = mod.ExecutiveConversationEngine(tmp)
            planner_state = ece.memory.plan(
                "هل أنت جاهز؟",
                running_tasks=self._stalled_tasks(),
            )
            draft = "نعم، أنا جاهز."
            result = ece.execute(
                query="هل أنت جاهز؟",
                draft_reply=draft,
                planner_state=planner_state,
                running_tasks=self._stalled_tasks(),
                reasoning_output=self._make_reasoning_output("question"),
                dry_run=True,
            )
            reply = result["reply"]
            self.assertNotIn("مهام مفتوحة تشغل موارد", reply,
                             "Task warning must not appear in conversational reply")
            self.assertNotIn("نغلق المهمة المفتوحة الأعلى أثرًا أولًا", reply,
                             "Task close instruction must not appear in conversational reply")
            self.assertEqual(reply, draft,
                             "Draft reply must be returned unchanged for conversational request")

    def test_execution_request_with_stalled_tasks_still_triggers_executive_signal(self):
        """request_type=execution + stalled tasks → executive signal must remain active."""
        mod = self._load_ece()
        with tempfile.TemporaryDirectory() as tmp:
            ece = mod.ExecutiveConversationEngine(tmp)
            planner_state = ece.memory.plan(
                "ابدأ مشروع التوسعة الجديد",
                running_tasks=self._stalled_tasks(),
            )
            result = ece.execute(
                query="ابدأ مشروع التوسعة الجديد",
                draft_reply="سأبدأ المشروع.",
                planner_state=planner_state,
                running_tasks=self._stalled_tasks(),
                reasoning_output=self._make_reasoning_output("execution"),
                dry_run=True,
            )
            reply = result["reply"]
            # For execution requests with stalled tasks the executive warning must appear
            self.assertTrue(
                "مهام مفتوحة" in reply or "نغلق" in reply or "مفتوح" in reply,
                f"Executive signal expected for execution request with stalled tasks, got: {reply!r}",
            )

    def test_greeting_with_stalled_tasks_does_not_leak_task_warning(self):
        """request_type=greeting + stalled tasks → conversational pass-through."""
        mod = self._load_ece()
        with tempfile.TemporaryDirectory() as tmp:
            ece = mod.ExecutiveConversationEngine(tmp)
            planner_state = ece.memory.plan(
                "مرحبا",
                running_tasks=self._stalled_tasks(),
            )
            draft = "أهلًا! كيف أقدر أساعدك؟"
            result = ece.execute(
                query="مرحبا",
                draft_reply=draft,
                planner_state=planner_state,
                running_tasks=self._stalled_tasks(),
                reasoning_output=self._make_reasoning_output("greeting"),
                dry_run=True,
            )
            reply = result["reply"]
            self.assertNotIn("مهام مفتوحة تشغل موارد", reply)
            self.assertNotIn("نغلق المهمة المفتوحة الأعلى أثرًا أولًا", reply)


if __name__ == "__main__":
    unittest.main()
