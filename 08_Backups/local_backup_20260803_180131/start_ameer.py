import os
import socket
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)


def find_free_port(start_port: int, max_tries: int = 20) -> int:
    for port in range(start_port, start_port + max_tries):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError("No free local port found")


requested_port = int(os.environ.get("AMEER_PORT", "8011"))
port = find_free_port(requested_port)
cmd = [
    sys.executable,
    "-m",
    "uvicorn",
    "ameer_server:app",
    "--host",
    "127.0.0.1",
    "--port",
    str(port),
    "--log-level",
    "info",
]

print("Starting Ameer...")
print("Working directory:", ROOT)
print("Command:", " ".join(cmd))
print("Open: http://127.0.0.1:" + str(port) + "/")

raise SystemExit(subprocess.call(cmd))
