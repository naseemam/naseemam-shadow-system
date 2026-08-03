import unittest

from fastapi.testclient import TestClient

from ameer_server import app


class WorkspaceShellTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_homepage_renders_workspace_shell_without_auth_gate(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        html = response.text
        self.assertIn("workspaceShell", html)
        self.assertNotIn("تسجيل دخول المؤسس", html)
        self.assertNotIn("founder@ameer.local", html)
        self.assertNotIn("Ameer2026!", html)

    def test_auth_routes_are_not_available(self):
        for path in ["/auth/login", "/auth/session", "/auth/logout", "/auth/protected"]:
            response = self.client.get(path)
            self.assertEqual(response.status_code, 404, msg=f"Expected 404 for {path}")


if __name__ == "__main__":
    unittest.main()
