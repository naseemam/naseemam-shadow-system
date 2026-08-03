import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ameer_runtime import resolve_host, resolve_port
payload = json.dumps({'query':'أضف سطرًا جديدًا في meeting.md يقول "إحضار التقرير المالي"','max_results':8}).encode('utf-8')
req = urllib.request.Request(f'http://{resolve_host()}:{resolve_port()}/ask', data=payload, headers={'Content-Type':'application/json; charset=utf-8'}, method='POST')
with urllib.request.urlopen(req, timeout=20) as resp:
    body = json.load(resp)
print(json.dumps({'build_id': body.get('build_id'), 'commit': body.get('commit'), 'port': body.get('port'), 'reply': body.get('reply')}, ensure_ascii=False, indent=2))
