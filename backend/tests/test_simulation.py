import pandas as pd

import backend.app.simulation.runtime as runtime_module
from backend.app.simulation.runtime import reset_runtime_for_tests


def _tiny_events() -> pd.DataFrame:
    rows = [
        dict(t=10, day=0, hour=7, dow=0, cell=0, user=1, value=40, n_items=1, order_id=1, small=1),
        dict(t=12, day=0, hour=7, dow=0, cell=0, user=2, value=50, n_items=1, order_id=2, small=1),
        dict(t=40, day=0, hour=7, dow=0, cell=0, user=3, value=200, n_items=2, order_id=3, small=0),
    ]
    return pd.DataFrame(rows)


def test_events_are_processed_in_time_order():
    rt = reset_runtime_for_tests(_tiny_events(), start_day=0)
    times = []
    for _ in range(3):
        out = rt.step(1)
        times.append(out["last_event"]["ingested"]["t"])
    assert times == sorted(times)
    assert rt.event_index == 3


def test_duplicate_csv_event_not_reingested():
    rt = reset_runtime_for_tests(_tiny_events(), start_day=0)
    rt.step(1)
    n = len(rt.orders)
    rt.event_index = 0
    rt._step_one()
    assert len(rt.orders) == n


def test_future_events_not_visible_before_clock():
    rt = reset_runtime_for_tests(_tiny_events(), start_day=0)
    rt.step(1)
    assert 2 not in rt.orders
    assert rt.clock < 12


def test_start_pause_reset():
    rt = reset_runtime_for_tests(_tiny_events(), start_day=0)
    rt.step(1)
    st = rt.pause()
    assert st["status"] == "paused"
    rt.start()
    rt.pause()
    rt.reset(persist_customers=False, start_day=0)
    assert rt.event_index == 0
    assert rt.orders == {}


def test_order_creation_and_tracking():
    rt = reset_runtime_for_tests(_tiny_events(), start_day=0)
    order = rt.place_customer_order(
        [{"item_id": "FDA15", "item_type": "Dairy", "unit_price": 40, "quantity": 1}],
        cell=0,
        customer_name="Test",
    )
    track = rt.tracking(order["order_id"])
    assert track["order"]["status"] == "placed"
    assert track["stages"][0]["done"] is True
    assert track["stages"][-1]["done"] is False
    rt.step(5)
    later = rt.get_order(order["order_id"])
    assert later is not None
    assert later["source"] == "checkout"


def test_waiting_orders_form_a_three_customer_pool_at_the_cap(monkeypatch):
    events = pd.DataFrame(
        [
            dict(t=t, day=0, hour=7, dow=0, cell=0, user=user, value=40, n_items=1, order_id=user, small=1)
            for t, user in ((10, 1), (11, 2), (12, 3))
        ]
    )
    monkeypatch.setattr(
        runtime_module,
        "predict_from_base",
        lambda base, wait, radius: ({}, {"probability": 0.99, "predicted_class": 1}),
    )
    rt = reset_runtime_for_tests(events, start_day=0)
    rt.step(3)

    assert all(rt.orders[order_id]["status"] == "dispatched" for order_id in (1, 2, 3))
    assert all(rt.orders[order_id]["decision"] == "POOL" for order_id in (1, 2, 3))
    assert set(rt.orders[1]["partner_order_ids"]) == {2, 3}


def test_checkout_forecast_keeps_model_probability_when_policy_would_not_wait(monkeypatch):
    monkeypatch.setattr(
        runtime_module,
        "predict_from_base",
        lambda base, wait, radius: (
            {},
            {"probability": wait / 100 + radius / 10_000},
        ),
    )
    rt = reset_runtime_for_tests(_tiny_events(), start_day=0)

    estimate = rt.estimate_checkout(value=31, n_items=1)

    assert estimate["partner_probability"] == 0.24
    assert estimate["recommended_wait_minutes"] == 15
    assert estimate["radius_m"] == 900
    assert "historical_demand_change_percent" in estimate


def test_checkout_forecast_does_not_claim_model_support_for_large_basket(monkeypatch):
    rt = reset_runtime_for_tests(_tiny_events(), start_day=0)

    estimate = rt.estimate_checkout(value=149, n_items=2)

    assert estimate["partner_probability"] is None
    assert estimate["recommended_wait_minutes"] == 0
