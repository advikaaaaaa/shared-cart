from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.simulation.runtime import reset_runtime_for_tests
import backend.app.api.routes as routes
import pandas as pd


client = TestClient(app)


def sign_in_test_admin(monkeypatch):
    monkeypatch.setenv("SHAREDCART_ADMIN_USERNAME", "ops")
    monkeypatch.setenv("SHAREDCART_ADMIN_PASSWORD", "test-password")
    monkeypatch.setenv("SHAREDCART_ADMIN_SECRET", "test-secret-at-least-32-chars-long")
    response = client.post(
        "/api/admin/login", json={"username": "ops", "password": "test-password"}
    )
    assert response.status_code == 200


def checkout_item(quantity=1):
    item = client.get("/api/catalog?limit=1").json()["items"][0]
    return {
        "item_id": item["item_id"],
        "item_type": item["item_type"],
        "unit_price": item["item_price"],
        "quantity": quantity,
    }


def test_health_and_validation():
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["product"] == "SharedCart"
    assert body["ok"] is True


def test_checkout_rejects_empty_cart():
    r = client.post("/api/orders", json={"cell": 0, "customer_name": "A", "items": []})
    assert r.status_code == 400


def test_prediction_rejects_invalid_wait(monkeypatch):
    sign_in_test_admin(monkeypatch)
    r = client.post("/api/predictions", json={"order_id": 1, "wait_minutes": 3, "radius_m": 600})
    assert r.status_code == 400
    client.post("/api/admin/logout")


def test_unknown_dataset(monkeypatch):
    sign_in_test_admin(monkeypatch)
    r = client.get("/api/datasets/not-a-file")
    assert r.status_code == 404
    client.post("/api/admin/logout")


def test_catalog_endpoint():
    r = client.get("/api/catalog?limit=5&page=1")
    assert r.status_code == 200
    data = r.json()
    assert "sample grocery" in data["disclaimer"].lower() or "grocery" in data["disclaimer"].lower()
    assert len(data["items"]) == 5
    next_page = client.get("/api/catalog?limit=5&page=2").json()
    assert next_page["count"] == data["count"]
    assert len(next_page["items"]) == 5
    assert {item["item_id"] for item in data["items"]}.isdisjoint(
        item["item_id"] for item in next_page["items"]
    )


def test_pooling_estimate_does_not_require_customer_area(monkeypatch):
    calls = {}

    class Runtime:
        def estimate_checkout(self, value, n_items, cell):
            calls.update(value=value, n_items=n_items, cell=cell)
            return {"partner_probability": 0.25, "recommended_wait_minutes": 5}

    monkeypatch.setattr(routes, "get_runtime", lambda: Runtime())
    response = client.post(
        "/api/pooling/estimate", json={"value": 31, "n_items": 1}
    )

    assert response.status_code == 200
    assert calls == {"value": 31, "n_items": 1, "cell": 44}
    assert "cell" not in response.json()


def test_order_roundtrip():
    reset_runtime_for_tests(
        pd.DataFrame(
            [dict(t=10, day=0, hour=7, dow=0, cell=0, user=1, value=40, n_items=1, order_id=1, small=1)]
        ),
        start_day=0,
    )
    item = checkout_item(quantity=2)
    r = client.post(
        "/api/orders",
        json={
            "cell": 0,
            "customer_name": "Guest",
            "items": [item],
        },
    )
    assert r.status_code == 200
    order = r.json()["order"]
    t = client.get(
        f"/api/orders/{order['order_id']}/tracking",
        headers={"X-Order-Access-Key": r.json()["access_key"]},
    )
    assert t.status_code == 200
    assert t.json()["stages"][0]["key"] == "placed"


def test_order_details_require_private_access_key():
    reset_runtime_for_tests(
        pd.DataFrame(
            [dict(t=10, day=0, hour=7, dow=0, cell=0, user=1, value=40, n_items=1, order_id=1, small=1)]
        ),
        start_day=0,
    )
    item = checkout_item()
    response = client.post(
        "/api/orders",
        json={
            "cell": 0,
            "customer_name": "Private customer",
            "items": [item],
        },
    )
    assert response.status_code == 200
    order_id = response.json()["order"]["order_id"]
    access_key = response.json()["access_key"]
    assert client.get(f"/api/orders/{order_id}", headers={"X-Order-Access-Key": "wrong"}).status_code == 404

    details = client.get(
        f"/api/orders/{order_id}", headers={"X-Order-Access-Key": access_key}
    )
    assert details.status_code == 200
    customer_order = details.json()["order"]
    assert customer_order["items"][0]["item_id"] == item["item_id"]
    assert "cell" not in customer_order
    assert "user_id" not in customer_order
    assert "access_key_hash" not in customer_order
    tracking = client.get(
        f"/api/orders/{order_id}/tracking", headers={"X-Order-Access-Key": access_key}
    )
    assert tracking.status_code == 200
    assert "cell" not in tracking.json()["order"]

    reset_runtime_for_tests(
        pd.DataFrame(
            [dict(t=10, day=0, hour=7, dow=0, cell=0, user=1, value=40, n_items=1, order_id=1, small=1)]
        ),
        start_day=0,
    )
    persisted = client.get(
        f"/api/orders/{order_id}", headers={"X-Order-Access-Key": access_key}
    )
    assert persisted.status_code == 200


def test_checkout_rejects_client_modified_price():
    item = checkout_item()
    item["unit_price"] += 1
    response = client.post(
        "/api/orders", json={"cell": 0, "customer_name": "Guest", "items": [item]}
    )
    assert response.status_code == 409


def test_operations_routes_require_admin_auth(monkeypatch):
    for key in (
        "SHAREDCART_ADMIN_USERNAME",
        "SHAREDCART_ADMIN_PASSWORD",
        "SHAREDCART_ADMIN_SECRET",
    ):
        monkeypatch.delenv(key, raising=False)
    assert client.get("/api/ops/dashboard").status_code == 401

    monkeypatch.setenv("SHAREDCART_ADMIN_USERNAME", "ops")
    monkeypatch.setenv("SHAREDCART_ADMIN_PASSWORD", "test-password")
    monkeypatch.setenv("SHAREDCART_ADMIN_SECRET", "test-secret-at-least-32-chars-long")
    assert client.post(
        "/api/admin/login", json={"username": "ops", "password": "wrong"}
    ).status_code == 401
    login = client.post(
        "/api/admin/login", json={"username": "ops", "password": "test-password"}
    )
    assert login.status_code == 200
    assert client.get("/api/ops/dashboard").status_code == 200
    assert client.post("/api/admin/logout").status_code == 200
    assert client.get("/api/ops/dashboard").status_code == 401
