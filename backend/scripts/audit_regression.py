"""Local integration regressions: run against a running API and real Redis/Postgres.

Creates an isolated test tenant; never uses existing business records.
Usage: .venv/Scripts/python.exe scripts/audit_regression.py
"""
import json
import sys
import urllib.error
import urllib.request
from decimal import Decimal
from uuid import uuid4


BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
if not BASE.startswith(("http://127.0.0.1:", "http://localhost:")):
    raise SystemExit("This regression runner accepts local APIs only")


def request(method, path, body=None, token=None, expected=200):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(BASE + path, data=json.dumps(body).encode() if body is not None else None,
                                 headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            code, raw = response.status, response.read().decode()
    except urllib.error.HTTPError as error:
        code, raw = error.code, error.read().decode()
    assert code == expected, f"{method} {path}: expected {expected}, got {code}: {raw[:300]}"
    try:
        return json.loads(raw)
    except ValueError:
        return raw


suffix = uuid4().hex[:10]
email, password = f"audit-{suffix}@example.com", f"AuditPass!{suffix}"
owner = request("POST", "/auth/register", {"email": email, "password": password,
                "tenant_name": f"Audit regression {suffix}", "tenant_slug": f"audit-{suffix}"})
token = owner["tokens"]["access_token"]
refresh = owner["tokens"]["refresh_token"]
for _ in range(3):
    rotated = request("POST", "/auth/refresh", {"refresh_token": refresh})
    request("POST", "/auth/refresh", {"refresh_token": refresh}, expected=401)
    refresh = rotated["refresh_token"]
    token = rotated["access_token"]
print("PASS: refresh rotation and replay rejection using Redis")

client = request("POST", "/clients/", {"name": "Regression client", "phone": "79001234567"}, token)
vehicle = request("POST", "/vehicles/", {"client_id": client["id"], "plate_number": "REG123",
                  "make_model": "Regression car"}, token)
order = request("POST", "/work-orders/", {"client_id": client["id"], "vehicle_id": vehicle["id"],
                "description": "Regression order", "total_amount": 1000}, token)
order_path = f'/work-orders/{order["id"]}'
employee = request("POST", "/employees/", {"email": f"manager-{suffix}@example.com",
                   "password": password, "role": "manager", "can_accept_payments": False}, token)
manager = request("POST", "/auth/login", {"email": employee["email"], "password": password})
manager_token = manager["tokens"]["access_token"]
assert request("GET", "/workspace/context", token=manager_token)["can_accept_payments"] is False
request("POST", order_path + "/payments", {"amount": 123, "method": "cash"}, manager_token, expected=403)
employee_path = f'/employees/{employee["employee_id"]}'
request("PATCH", employee_path, {"can_accept_payments": True}, token)
request("GET", "/auth/me", token=manager_token, expected=401)
request("POST", "/auth/refresh", {"refresh_token": manager["tokens"]["refresh_token"]}, expected=401)
manager_token = request("POST", "/auth/login", {"email": employee["email"], "password": password})["tokens"]["access_token"]
assert request("GET", "/workspace/context", token=manager_token)["can_accept_payments"] is True
payment = request("POST", order_path + "/payments", {"amount": 123, "method": "cash", "comment": "VOID-MARKER"}, manager_token)
request("POST", order_path + f'/payments/{payment["id"]}/void', {"reason": "Regression correction"}, token)
document = request("GET", order_path + "/document?format=html&locale=en", token=token)
assert "VOID-MARKER" not in document and "123.00" not in document and "123,00" not in document
request("GET", "/auth/me", token=manager_token)  # Warm membership cache before disabling.
request("PATCH", employee_path + "/status", {"is_active": False}, token)
request("GET", "/clients/", token=manager_token, expected=403)
print("PASS: payment permission, voided document, status-only disable and cached-session denial")

history_orders = []
for index in range(51):
    history_orders.append(request("POST", "/work-orders/", {"client_id": client["id"], "vehicle_id": vehicle["id"],
            "description": f"History regression {index}", "total_amount": 10}, token))
cancelled = request("POST", "/work-orders/", {"client_id": client["id"], "vehicle_id": vehicle["id"],
                    "description": "Cancelled debt exclusion", "total_amount": 999}, token)
request("POST", f'/work-orders/{cancelled["id"]}/status', {"status": "cancelled"}, token)
for path in (f'/clients/{client["id"]}/work-orders', f'/vehicles/{vehicle["id"]}/history'):
    first = request("GET", path + "?limit=50&offset=0", token=token)
    second = request("GET", path + "?limit=50&offset=50", token=token)
    assert len(first) == 50 and len(second) == 3
    assert len({row["id"] for row in first + second}) == 53
totals = request("GET", f'/clients/{client["id"]}', token=token)
assert Decimal(totals["total_paid"]) == 0 and Decimal(totals["total_debt"]) == 1510, totals
print("PASS: 53-visit history pagination; all-history debt excludes cancelled orders and voided payments")

registry = request("GET", "/work-orders/?limit=1", token=token)
assert len(registry["items"]) == 1 and registry["summary"]["unassigned_count"] == 52
assert Decimal(registry["summary"]["outstanding_amount"]) == 1510
for item in history_orders:
    request("POST", f'/work-orders/{item["id"]}/status', {"status": "cancelled"}, token)
queue = request("GET", "/work-orders/?limit=8&status_scope=active", token=token)
assert [item["id"] for item in queue["items"]] == [order["id"]]
assert Decimal(queue["summary"]["outstanding_amount"]) == 1000
print("PASS: full-registry metrics and old active order behind 52 more recent cancelled orders")

request("POST", "/auth/change-password", {"current_password": password, "new_password": password + "-new"}, token, expected=204)
request("POST", "/auth/refresh", {"refresh_token": refresh}, expected=401)
request("GET", "/auth/me", token=token, expected=401)
request("POST", "/auth/login", {"email": email, "password": password}, expected=401)
fresh = request("POST", "/auth/login", {"email": email, "password": password + "-new"})
request("POST", "/auth/logout", {"refresh_token": fresh["tokens"]["refresh_token"]}, expected=204)
request("POST", "/auth/refresh", {"refresh_token": fresh["tokens"]["refresh_token"]}, expected=401)
print("PASS: password rotation and logout invalidate refresh tokens")
print(f"All regressions passed in isolated tenant audit-{suffix}")
