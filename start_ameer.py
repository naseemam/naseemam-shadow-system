import os
import importlib.util
import socket
import subprocess
import sys
from pathlib import Path

from ameer_runtime import DEFAULT_PORT, resolve_port

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)


def port_is_busy(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return sock.connect_ex((host, port)) == 0


def ensure_runtime_dependency(module_name: str, package_name: str | None = None) -> None:
    if importlib.util.find_spec(module_name) is not None:
        return

    package = package_name or module_name
    raise SystemExit(
        f"Missing required dependency '{package}'. "
        f"Install project dependencies first with: {sys.executable} -m pip install -r requirements.txt"
    )


host = "0.0.0.0"
port = resolve_port()
os.environ["AMEER_PORT"] = str(port)
ensure_runtime_dependency("uvicorn", "uvicorn[standard]")
cmd = [
    sys.executable,
    "-m",
    "uvicorn",
    "ameer_server:app",
    "--host",
    host,
    "--port",
    str(port),
    "--log-level",
    "info",
]

if port_is_busy(host, port):
    raise SystemExit(
        f"Ameer runtime refused to start because {host}:{port} is already in use. "
        f"Use the single shared runtime port {DEFAULT_PORT} or stop the old process first."
    )

print("Starting Ameer launcher...")
print("Working directory:", ROOT)
print("Command:", " ".join(cmd))
print(f"Open: http://{host}:{port}/")

raise SystemExit(subprocess.call(cmd))
