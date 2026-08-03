import traceback
import ameer_server
print('imported')
print(type(ameer_server.app).__name__)
try:
    from fastapi.testclient import TestClient
    client = TestClient(ameer_server.app)
    resp = client.post('/ask', json={'query':'مرحبا','max_results':3})
    print('status', resp.status_code)
    print(resp.text)
except Exception as exc:
    print('ERROR', type(exc).__name__, exc)
    traceback.print_exc()
