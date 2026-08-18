import json
import os
import signal
import subprocess
import time
from urllib.parse import quote
from urllib.request import Request, urlopen

ROOT = os.path.dirname(os.path.dirname(__file__))
proc = subprocess.Popen(["python3", "start_ameer.py"], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def request(method, path, payload=None):
    body = None if payload is None else json.dumps(payload, ensure_ascii=False).encode()
    req = Request("http://127.0.0.1:8000" + quote(path, safe="/"), data=body, method=method, headers={"Content-Type": "application/json"})
    with urlopen(req, timeout=10) as response:
        return response.status, json.loads(response.read().decode())

try:
    time.sleep(4)
    status, created = request("POST", "/test/commerce/orders", {"customer_name": "عميلة HTTP اختبار", "total": 199})
    assert status == 201 and created["no_real_money"] is True
    order_id = created["order"]["id"]
    status, session = request("POST", f"/test/commerce/orders/{order_id}/payment-session")
    assert status == 200 and session["no_real_charge"] is True
    event = {"event_id": "http-event-1", "order_id": order_id, "event_type": "payment.updated", "status": "paid"}
    status, paid = request("POST", "/test/commerce/webhooks/payment", event)
    assert status == 200 and paid["status"] == "processed"
    status, duplicate = request("POST", "/test/commerce/webhooks/payment", event)
    assert status == 200 and duplicate["status"] == "duplicate_ignored"
    status, shipment = request("POST", f"/test/commerce/orders/{order_id}/shipment", {"provider": "test_carrier"})
    assert status == 200 and shipment["no_real_shipment"] is True
    status, snapshot = request("GET", "/test/commerce/snapshot")
    assert status == 200 and snapshot["no_real_money"] is True and snapshot["no_real_shipments"] is True
    print("commerce_test_api: PASS")
finally:
    proc.send_signal(signal.SIGTERM)
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
