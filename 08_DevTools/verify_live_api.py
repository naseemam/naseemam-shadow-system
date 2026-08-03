import json
import urllib.request

body = json.dumps({"query": "انشي ملفا باسم test_from_browser.txt يحتوي على مرحبا", "max_results": 3}).encode("utf-8")
req = urllib.request.Request(
    "http://127.0.0.1:8000/ask",
    data=body,
    headers={"Content-Type": "application/json; charset=utf-8"},
    method="POST",
)
with urllib.request.urlopen(req, timeout=60) as resp:
    data = json.loads(resp.read().decode("utf-8"))
    print(json.dumps({k: data.get(k) for k in ["intent", "routing", "reply", "execution_engine", "reply_meta", "executive_brain"]}, ensure_ascii=False, indent=2))
