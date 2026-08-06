import json
import os
import socket
import subprocess
import sys
import time
import unittest

from urllib import request as urllib_request


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        sock.listen(1)
        return int(sock.getsockname()[1])


def _http_get_json(url: str) -> dict:
    with urllib_request.urlopen(url, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def _http_post_json(url: str, payload: dict) -> tuple[int, dict]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib_request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    with urllib_request.urlopen(req, timeout=10) as response:
        return response.status, json.loads(response.read().decode("utf-8"))


class AskEndpointSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.port = _find_free_port()
        cls.base_url = f"http://127.0.0.1:{cls.port}"
        cls.server = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "ameer_server:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(cls.port),
            ],
            cwd=ROOT,
            env={**os.environ, "AMEER_PORT": str(cls.port)},
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        deadline = time.time() + 15
        while time.time() < deadline:
            if cls.server.poll() is not None:
                raise RuntimeError("Smoke test server exited before becoming healthy")
            try:
                health = _http_get_json(f"{cls.base_url}/health")
                if health.get("status") == "ok":
                    return
            except Exception:
                pass
            time.sleep(0.25)

        raise RuntimeError("Smoke test server did not become healthy in time")

    @classmethod
    def tearDownClass(cls):
        if getattr(cls, "server", None) is None:
            return
        if cls.server.poll() is None:
            cls.server.terminate()
            try:
                cls.server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                cls.server.kill()
                cls.server.wait(timeout=5)

    def test_ask_endpoint_returns_user_safe_contract(self):
        health = _http_get_json(f"{self.base_url}/health")
        status_code, data = _http_post_json(
            f"{self.base_url}/ask",
            {"query": "مرحبا", "max_results": 3},
        )
        self.assertEqual(status_code, 200)

        self.assertIn("reply", data)
        self.assertIsInstance(data["reply"], str)
        self.assertTrue(data["reply"].strip())
        self.assertEqual(data.get("assistant"), "أمير")
        self.assertEqual(data.get("message"), data.get("reply"))
        self.assertEqual(data.get("build_id"), health.get("build_id"))
        self.assertEqual(data.get("build"), health.get("build"))
        self.assertEqual(data.get("commit"), health.get("commit"))
        self.assertNotIn("port", data)
        self.assertNotIn("workspace", data)
        self.assertNotIn("routing", data)
        self.assertNotIn("selected_agent", data)
        self.assertNotIn("agent_result", data)
        self.assertNotIn("agent_brain_payload", data)
        self.assertNotIn("execution_engine", data)
        self.assertNotIn("debug_trace", data)
        self.assertNotIn("_agent", data["reply"].lower())
        self.assertNotIn(".md", data["reply"].lower())
        self.assertNotIn("prompt", data["reply"].lower())

    def test_health_endpoint_exposes_runtime_identity(self):
        data = _http_get_json(f"{self.base_url}/health")
        self.assertEqual(data.get("status"), "ok")
        self.assertTrue(data.get("build_id"))
        self.assertEqual(data.get("build"), data.get("build_id"))
        self.assertTrue(data.get("commit"))
        self.assertTrue(data.get("started_at"))
        # Internal fields must NOT be exposed publicly
        self.assertNotIn("port", data)
        self.assertNotIn("workspace", data)
        self.assertNotIn("pid", data)
        self.assertNotIn("host", data)
        self.assertNotIn("entrypoint", data)

    def test_execute_endpoint_returns_task_object_for_home_page(self):
        status_code, data = _http_post_json(
            f"{self.base_url}/execute",
            {"task": "أنشئ صفحة home", "max_results": 3},
        )
        self.assertEqual(status_code, 200)
        self.assertEqual(data.get("mode"), "execute")
        self.assertEqual(data.get("task_count"), 1)
        self.assertEqual(data.get("sandbox_root"), "09_Assets/runtime_workspace")
        self.assertIn("tasks", data)
        self.assertEqual(data["tasks"][0]["action"], "create_file")
        self.assertEqual(data["tasks"][0]["executor"], "file")
        self.assertEqual(data["tasks"][0]["target"], "09_Assets/runtime_workspace/home/index.html")
        self.assertTrue(data["tasks"][0]["metadata"]["sandboxed"])
        self.assertIn("<html", data["tasks"][0]["inputs"]["content"].lower())


if __name__ == "__main__":
    unittest.main()
