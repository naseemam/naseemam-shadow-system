import importlib.util
import os
import sys
import unittest
from unittest.mock import patch


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MODULE_PATH = os.path.join(ROOT, "start_ameer.py")


class StartAmeerLauncherTests(unittest.TestCase):
    def test_launcher_exits_with_install_help_when_uvicorn_is_missing(self):
        spec = importlib.util.spec_from_file_location("start_ameer_missing_uvicorn", MODULE_PATH)
        module = importlib.util.module_from_spec(spec)

        with patch("importlib.util.find_spec", side_effect=lambda name: None if name == "uvicorn" else object()):
            with self.assertRaises(SystemExit) as ctx:
                spec.loader.exec_module(module)

        message = str(ctx.exception)
        self.assertIn("Missing required dependency 'uvicorn[standard]'", message)
        self.assertIn(f"{sys.executable} -m pip install -r requirements.txt", message)


if __name__ == "__main__":
    unittest.main()
