import numpy as np
import pandas as pd

from backend.app.ml.live_features import EventIndex, causal_candidates
from backend.app.ml.simulate import add_engineered_features, engineer_row, neighbours


def test_neighbours_chebyshev():
    nb = neighbours(55, 0)
    assert nb == [55]
    nb1 = neighbours(0, 1)
    assert 0 in nb1 and 1 in nb1 and 10 in nb1
    assert 22 not in nb1


def test_engineer_row_matches_batch():
    base = dict(
        hour=13,
        day_of_week=2,
        is_weekend=0,
        is_peak_hour=1,
        grid_row=5,
        grid_col=5,
        zone_type="commercial",
        order_value=80,
        n_items=2,
        orders_in_cell_last_15min=3,
        avg_orders_in_cell_this_hour=4.0,
        user_past_order_count=2,
        user_small_order_ratio=0.5,
        small_orders_300m_last_15min=1,
        small_orders_600m_last_15min=2,
        small_orders_900m_last_15min=4,
    )
    df = pd.DataFrame([{**base, "wait_minutes": 8, "radius_m": 600, "split": "train"}])
    df2, cap = add_engineered_features(df, busy_cap=10.44)
    row = engineer_row(base, 8, 600, 10.44)
    assert abs(row["hour_sin"] - df2.hour_sin.iloc[0]) < 1e-9
    assert row["recent_in_chosen_radius"] == 2
    assert abs(row["expected_arrivals"] - 2 / 15 * 8) < 1e-9
    assert row["wait_x_cells"] == 8 * 9
    assert cap == 10.44


def test_causal_candidates_ignore_future():
    idx = EventIndex()
    zone = np.array(["quiet"] * 100)
    events = pd.DataFrame(
        [
            dict(t=10, day=0, hour=7, dow=0, cell=0, user=1, value=40, n_items=1, order_id=1, small=1),
            dict(t=14, day=0, hour=7, dow=0, cell=0, user=2, value=50, n_items=1, order_id=2, small=1),
            dict(t=30, day=0, hour=7, dow=0, cell=0, user=3, value=50, n_items=1, order_id=3, small=1),
        ]
    )
    for r in events.itertuples(index=False):
        idx.observe(r)
    cands = causal_candidates(idx, 0, 10, 1, 300, 8, arrived_max_t=14)
    ids = [c["order_id"] for c in cands]
    assert 2 in ids
    assert 3 not in ids
