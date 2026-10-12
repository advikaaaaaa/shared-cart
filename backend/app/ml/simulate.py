"""Reproduce CapstoneProject.ipynb order simulation and training-row construction."""

from __future__ import annotations

import bisect
from typing import Any

import numpy as np
import pandas as pd

from backend.app.ml.catalog import load_or_build_catalog
from backend.app.ml.constants import (
    CLOSE_HOUR,
    GRID,
    N_USERS,
    OPEN_HOUR,
    ORDERS_PER_DAY,
    RADII,
    SEED,
    THRESHOLD,
    TOTAL_DAYS,
    TRAIN_LAST_DAY,
    WAITS,
    WARMUP_DAYS,
)
from backend.app.paths import CATALOG_CSV, EVENTS_CSV, TRAINING_CSV, ensure_dirs


def _hour_profile(peaks: list[tuple[float, float, float]]) -> np.ndarray:
    h = np.arange(24, dtype=float)
    p = np.full(24, 0.05)
    for centre_h, width, amp in peaks:
        p += amp * np.exp(-0.5 * ((h - centre_h) / width) ** 2)
    p[(h < OPEN_HOUR) | (h >= CLOSE_HOUR)] = 0
    return p / p.sum()


def neighbours(cell: int, k: int) -> list[int]:
    r, c = divmod(cell, GRID)
    return [
        r_ * GRID + c_
        for r_ in range(max(0, r - k), min(GRID, r + k + 1))
        for c_ in range(max(0, c - k), min(GRID, c + k + 1))
    ]


def build_zones(rng: np.random.Generator) -> np.ndarray:
    rr, cc = np.divmod(np.arange(GRID * GRID), GRID)
    d_hub = np.minimum(np.hypot(rr - 2, cc - 2), np.hypot(rr - 7, cc - 7))
    d_cen = np.hypot(rr - 4.5, cc - 4.5)
    zone = np.empty(GRID * GRID, dtype=object)
    for i in range(GRID * GRID):
        noise = rng.normal(0, 0.6)
        if d_cen[i] + noise < 1.8:
            zone[i] = "commercial"
        elif d_hub[i] + noise < 2.2:
            zone[i] = "dense_residential"
        elif d_hub[i] + noise < 4.0:
            zone[i] = "normal_residential"
        else:
            zone[i] = "quiet"
    return zone


def simulate_orders(
    catalog: pd.DataFrame,
    rng: np.random.Generator,
    zone: np.ndarray,
    *,
    n_users: int = N_USERS,
    total_days: int = TOTAL_DAYS,
    orders_per_day: int = ORDERS_PER_DAY,
) -> pd.DataFrame:
    zw_map = {
        "dense_residential": 4.0,
        "normal_residential": 2.0,
        "commercial": 2.5,
        "quiet": 0.4,
    }
    zw = np.array([zw_map[z] for z in zone])
    prof_res = _hour_profile([(9, 1.2, 0.4), (13, 1.3, 0.6), (20, 1.6, 1.0)])
    prof_com = _hour_profile([(9, 1.0, 0.3), (13, 1.2, 1.0), (17, 1.2, 0.4)])
    cell_users = rng.choice(GRID * GRID, size=n_users, p=zw / zw.sum())
    user_activity = rng.lognormal(0, 0.8, n_users)
    users_by_cell = {c: np.where(cell_users == c)[0] for c in range(GRID * GRID)}

    rows: list[tuple] = []
    for day in range(total_days):
        dow = day % 7
        weekend = dow >= 5
        lam = np.zeros((24, GRID * GRID))
        for c in range(GRID * GRID):
            p = prof_com if zone[c] == "commercial" else prof_res
            if zone[c] == "commercial":
                f = 0.5 if weekend else 1.0
            else:
                f = 1.2 if weekend else 1.0
            lam[:, c] = zw[c] * p * f
        lam *= orders_per_day / lam.sum()
        counts = rng.poisson(lam)
        for h, c in zip(*np.nonzero(counts)):
            for _ in range(int(counts[h, c])):
                us = users_by_cell[c]
                if len(us) == 0:
                    continue
                w = user_activity[us]
                u = rng.choice(us, p=w / w.sum())
                n_items = int(rng.choice([1, 2, 3, 4], p=[0.65, 0.22, 0.10, 0.03]))
                pick = rng.integers(0, len(catalog), size=n_items)
                value = int(catalog.item_price.to_numpy()[pick].sum())
                t = day * 1440 + h * 60 + rng.uniform(0, 60)
                rows.append((t, day, int(h), dow, int(c), int(u), value, n_items))
    orders = pd.DataFrame(
        rows, columns=["t", "day", "hour", "dow", "cell", "user", "value", "n_items"]
    )
    orders = orders.sort_values("t").reset_index(drop=True)
    orders["order_id"] = np.arange(1, len(orders) + 1)
    orders["small"] = (orders.value < THRESHOLD).astype(int)
    return orders


def build_training_frame(
    orders: pd.DataFrame,
    zone: np.ndarray,
    *,
    warmup_days: int = WARMUP_DAYS,
    total_days: int = TOTAL_DAYS,
    train_last_day: int = TRAIN_LAST_DAY,
) -> pd.DataFrame:
    empty = np.array([])
    nb = {(c, k): neighbours(c, k) for c in range(GRID * GRID) for k in (0, 1, 2)}
    small = orders[orders.small == 1]
    s_times = {c: g.t.values for c, g in small.groupby("cell")}
    s_users = {c: g.user.values for c, g in small.groupby("cell")}
    a_times = {c: g.t.values for c, g in orders.groupby("cell")}
    max_day = int(orders.day.max()) + 1 if len(orders) else total_days
    cnt = np.zeros((max(total_days, max_day), 24, GRID * GRID))
    for d, h, c in zip(orders.day, orders.hour, orders.cell):
        cnt[d, h, c] += 1
    cum = np.cumsum(cnt, axis=0)

    user_n: dict[int, int] = {}
    user_s: dict[int, int] = {}
    base_rows: list[tuple[dict[str, Any], dict[int, float]]] = []
    for r in orders.itertuples(index=False):
        pn, ps = user_n.get(r.user, 0), user_s.get(r.user, 0)
        user_n[r.user] = pn + 1
        user_s[r.user] = ps + r.small
        if r.small == 0 or r.day < warmup_days or r.day > total_days - 2:
            continue
        avg_hist = cum[r.day - 1, r.hour, r.cell] / r.day
        ao = a_times.get(r.cell, empty)
        last15_cell = bisect.bisect_left(ao, r.t) - bisect.bisect_left(ao, r.t - 15)
        f = dict(
            order_id=r.order_id,
            user_id=r.user,
            day=r.day,
            hour=r.hour,
            day_of_week=r.dow,
            is_weekend=int(r.dow >= 5),
            is_peak_hour=int(r.hour in (12, 13, 19, 20, 21)),
            grid_cell_id=r.cell,
            grid_row=r.cell // GRID,
            grid_col=r.cell % GRID,
            zone_type=zone[r.cell],
            order_value=r.value,
            n_items=r.n_items,
            orders_in_cell_last_15min=last15_cell,
            avg_orders_in_cell_this_hour=round(float(avg_hist), 3),
            user_past_order_count=pn,
            user_small_order_ratio=round(ps / pn, 3) if pn else 0.0,
        )
        ttp: dict[int, float] = {}
        for metres, k in RADII.items():
            cnt15, first = 0, np.inf
            for cell in nb[(r.cell, k)]:
                st = s_times.get(cell, empty)
                cnt15 += bisect.bisect_left(st, r.t) - bisect.bisect_left(st, r.t - 15)
                su = s_users.get(cell, empty)
                i = bisect.bisect_right(st, r.t)
                while i < len(st) and st[i] - r.t <= 15:
                    if su[i] != r.user:
                        first = min(first, st[i] - r.t)
                        break
                    i += 1
            f[f"small_orders_{metres}m_last_15min"] = cnt15
            ttp[metres] = first
        base_rows.append((f, ttp))

    out = []
    for f, ttp in base_rows:
        for metres in RADII:
            for w in WAITS:
                row = dict(f)
                row["wait_minutes"] = w
                row["radius_m"] = metres
                row["partner_found"] = int(ttp[metres] <= w)
                out.append(row)
    df = pd.DataFrame(out)
    df["split"] = np.where(df.day <= train_last_day, "train", "test")
    return df


def add_engineered_features(df: pd.DataFrame, busy_cap: float | None = None) -> tuple[pd.DataFrame, float]:
    df2 = df.copy()
    df2["hour_sin"] = np.sin(2 * np.pi * df2.hour / 24)
    df2["hour_cos"] = np.cos(2 * np.pi * df2.hour / 24)
    df2["recent_in_chosen_radius"] = np.select(
        [df2.radius_m == 300, df2.radius_m == 600, df2.radius_m == 900],
        [
            df2.small_orders_300m_last_15min,
            df2.small_orders_600m_last_15min,
            df2.small_orders_900m_last_15min,
        ],
    )
    df2["expected_arrivals"] = df2.recent_in_chosen_radius / 15 * df2.wait_minutes
    df2["busy_ratio"] = df2.orders_in_cell_last_15min / (
        df2.avg_orders_in_cell_this_hour / 4 + 1e-3
    )
    if busy_cap is None:
        busy_cap = float(df2.loc[df2.split == "train", "busy_ratio"].quantile(0.99))
    df2["busy_ratio"] = df2.busy_ratio.clip(upper=busy_cap)
    df2["wait_x_cells"] = df2.wait_minutes * df2.radius_m.map({300: 1, 600: 9, 900: 25})
    df2["is_dense_zone"] = (df2.zone_type == "dense_residential").astype(int)
    return df2, float(busy_cap)


def engineer_row(
    base: dict[str, Any],
    wait_minutes: int,
    radius_m: int,
    busy_cap: float,
) -> dict[str, Any]:
    row = dict(base)
    row["wait_minutes"] = int(wait_minutes)
    row["radius_m"] = int(radius_m)
    row["hour_sin"] = float(np.sin(2 * np.pi * row["hour"] / 24))
    row["hour_cos"] = float(np.cos(2 * np.pi * row["hour"] / 24))
    if radius_m == 300:
        recent = row["small_orders_300m_last_15min"]
    elif radius_m == 600:
        recent = row["small_orders_600m_last_15min"]
    else:
        recent = row["small_orders_900m_last_15min"]
    row["recent_in_chosen_radius"] = int(recent)
    row["expected_arrivals"] = float(recent) / 15.0 * wait_minutes
    busy = row["orders_in_cell_last_15min"] / (row["avg_orders_in_cell_this_hour"] / 4 + 1e-3)
    row["busy_ratio"] = float(min(busy, busy_cap))
    row["wait_x_cells"] = int(wait_minutes * {300: 1, 600: 9, 900: 25}[radius_m])
    row["is_dense_zone"] = int(row["zone_type"] == "dense_residential")
    return row


def generate_core_datasets(
    force: bool = False,
    *,
    n_users: int = N_USERS,
    total_days: int = TOTAL_DAYS,
    warmup_days: int = WARMUP_DAYS,
    train_last_day: int = TRAIN_LAST_DAY,
    orders_per_day: int = ORDERS_PER_DAY,
) -> dict[str, Any]:
    ensure_dirs()
    catalog = load_or_build_catalog()
    if EVENTS_CSV.exists() and TRAINING_CSV.exists() and not force:
        orders = pd.read_csv(EVENTS_CSV)
        df = pd.read_csv(TRAINING_CSV)
        rng = np.random.default_rng(SEED)
        zone = build_zones(rng)
        return {"catalog": catalog, "orders": orders, "train_df": df, "zone": zone}

    rng = np.random.default_rng(SEED)
    zone = build_zones(rng)
    orders = simulate_orders(
        catalog,
        rng,
        zone,
        n_users=n_users,
        total_days=total_days,
        orders_per_day=orders_per_day,
    )
    df = build_training_frame(
        orders,
        zone,
        warmup_days=warmup_days,
        total_days=total_days,
        train_last_day=train_last_day,
    )
    df2, cap = add_engineered_features(df)
    orders.to_csv(EVENTS_CSV, index=False)
    df2.to_csv(TRAINING_CSV, index=False)
    catalog.to_csv(CATALOG_CSV, index=False)
    return {
        "catalog": catalog,
        "orders": orders,
        "train_df": df2,
        "zone": zone,
        "busy_cap": cap,
        "scale": {
            "n_users": n_users,
            "total_days": total_days,
            "warmup_days": warmup_days,
            "train_last_day": train_last_day,
            "orders_per_day": orders_per_day,
            "seed": SEED,
        },
    }
