import sys

sys.path.insert(0, ".")
sys.path.insert(0, "06_Code")

from ameer_server import app

routes = {}
for route in app.routes:
    path = getattr(route, "path", None)
    if path:
        routes.setdefault(path, set()).update(getattr(route, "methods", set()))
routes = {path: sorted(methods) for path, methods in routes.items()}
expected = {
    "/test/commerce/orders/{order_id}/shipment": ["GET", "POST"],
    "/test/commerce/webhooks/shipping": ["POST"],
    "/test/commerce/snapshot": ["GET"],
}
for path, methods in expected.items():
    actual = routes.get(path, [])
    for method in methods:
        assert method in actual, f"missing {method} {path}: {actual}"
print("shipping_routes: PASS")
for path in sorted(expected):
    print(path, routes[path])
