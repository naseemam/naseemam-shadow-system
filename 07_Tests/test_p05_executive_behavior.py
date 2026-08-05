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


if __name__ == "__main__":
    unittest.main()
