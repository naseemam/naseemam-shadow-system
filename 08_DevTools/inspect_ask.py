import json
import urllib.request
payload = json.dumps({'query':'أضف سطرًا جديدًا في meeting.md يقول "إحضار التقرير المالي"','max_results':8}).encode('utf-8')
req = urllib.request.Request('http://127.0.0.1:8011/ask', data=payload, headers={'Content-Type':'application/json; charset=utf-8'}, method='POST')
with urllib.request.urlopen(req, timeout=20) as resp:
    body = json.load(resp)
print(json.dumps({'intent': body.get('intent'), 'execution': body.get('execution_engine'), 'reply': body.get('reply')}, ensure_ascii=False, indent=2))
