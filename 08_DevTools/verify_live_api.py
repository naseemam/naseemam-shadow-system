import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ameer_runtime import resolve_host, resolve_port

body = json.dumps({"query": "انشي ملفا باسم test_from_browser.txt يحتوي على مرحبا", "max_results": 3}).encode("utf-8")
req = urllib.request.Request(
    f"http://{resolve_host()}:{resolve_port()}/ask",
    data=body,
    headers={"Content-Type": "application/json; charset=utf-8"},
    method="POST",
)
with urllib.request.urlopen(req, timeout=60) as resp:
    data = json.loads(resp.read().decode("utf-8"))
    print(json.dumps({k: data.get(k) for k in ["build_id", "commit", "port", "reply"]}, ensure_ascii=False, indent=2))
