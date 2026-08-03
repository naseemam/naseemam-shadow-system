import json
from fastapi.testclient import TestClient
import ameer_server

client = TestClient(ameer_server.app)
response = client.post(
    "/ask",
    json={"query": "أنشئ ملفًا باسم demo_notes.md يحتوي على مرحبا من أمير"},
)
print(response.status_code)
print(json.dumps(response.json(), ensure_ascii=False, indent=2))
