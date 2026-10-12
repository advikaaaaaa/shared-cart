import pandas as pd

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
