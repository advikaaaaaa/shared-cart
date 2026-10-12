from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.simulation.runtime import reset_runtime_for_tests
import pandas as pd


client = TestClient(app)


def test_health_and_validation():
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["product"] == "SharedCart"
    assert body["ok"] is True


def test_checkout_rejects_empty_cart():
    r = client.post("/api/orders", json={"cell": 0, "customer_name": "A", "items": []})
    assert r.status_code == 400


def test_prediction_rejects_invalid_wait():
    r = client.post("/api/predictions", json={"order_id": 1, "wait_minutes": 3, "radius_m": 600})
    assert r.status_code == 400


def test_unknown_dataset():
    r = client.get("/api/datasets/not-a-file")
    assert r.status_code == 404


def test_catalog_endpoint():
    r = client.get("/api/catalog?limit=5")
    assert r.status_code == 200
    data = r.json()
    assert "sample grocery" in data["disclaimer"].lower() or "grocery" in data["disclaimer"].lower()
    assert len(data["items"]) >= 1


def test_order_roundtrip():
    reset_runtime_for_tests(
        pd.DataFrame(
            [dict(t=10, day=0, hour=7, dow=0, cell=0, user=1, value=40, n_items=1, order_id=1, small=1)]
        ),
        start_day=0,
    )
    r = client.post(
        "/api/orders",
        json={
            "cell": 0,
            "customer_name": "Guest",
            "items": [{"item_id": "X", "item_type": "Dairy", "unit_price": 40, "quantity": 2}],
        },
    )
    assert r.status_code == 200
    oid = r.json()["order"]["order_id"]
    t = client.get(f"/api/orders/{oid}/tracking")
    assert t.status_code == 200
    assert t.json()["stages"][0]["key"] == "placed"
