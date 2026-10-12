"""Past-only feature construction for a focal order against an event window."""

from __future__ import annotations

import bisect
from dataclasses import dataclass, field
from typing import Any, Iterable

import numpy as np
import pandas as pd

from backend.app.ml.constants import GRID, PEAK_HOURS, RADII, TOTAL_DAYS
from backend.app.ml.simulate import engineer_row, neighbours


@dataclass
class EventIndex:
    """Sorted per-cell times for causal (past-only) lookups."""

    all_times: dict[int, list[float]] = field(default_factory=dict)
    all_users: dict[int, list[int]] = field(default_factory=dict)
    small_times: dict[int, list[float]] = field(default_factory=dict)
    small_users: dict[int, list[int]] = field(default_factory=dict)
    small_values: dict[int, list[float]] = field(default_factory=dict)
    small_ids: dict[int, list[int]] = field(default_factory=dict)
    hourly_counts: np.ndarray | None = field(default_factory=lambda: np.zeros((TOTAL_DAYS + 5, 24, GRID * GRID)))
    user_n: dict[int, int] = field(default_factory=dict)
    user_s: dict[int, int] = field(default_factory=dict)

    @classmethod
    def from_events(cls, events: pd.DataFrame) -> "EventIndex":
        idx = cls()
        idx.hourly_counts = np.zeros((TOTAL_DAYS + 5, 24, GRID * GRID))
        for r in events.itertuples(index=False):
            idx.observe(r, count_history=True)
        return idx

    def observe(self, r: Any, count_history: bool = True) -> None:
        cell = int(r.cell)
        t = float(r.t)
        user = int(r.user)
        self.all_times.setdefault(cell, []).append(t)
        self.all_users.setdefault(cell, []).append(user)
        if count_history and self.hourly_counts is not None:
            d = int(getattr(r, "day", t // 1440))
            h = int(getattr(r, "hour", (t % 1440) // 60))
            if 0 <= d < self.hourly_counts.shape[0] and 0 <= h < 24:
                self.hourly_counts[d, h, cell] += 1
        self.user_n[user] = self.user_n.get(user, 0) + 1
        small = int(getattr(r, "small", 0))
        self.user_s[user] = self.user_s.get(user, 0) + small
        if small:
            self.small_times.setdefault(cell, []).append(t)
            self.small_users.setdefault(cell, []).append(user)
            self.small_values.setdefault(cell, []).append(float(r.value))
            self.small_ids.setdefault(cell, []).append(int(r.order_id))

    def features_before(self, r: Any, zone: np.ndarray) -> dict[str, Any]:
        """Features using events with time < r.t and user history excluding this order.

        Call this BEFORE observe() for a newly arriving order, or pass a snapshot
        that already includes prior orders only.
        """
        cell = int(r.cell)
        t = float(r.t)
        user = int(r.user)
        day = int(getattr(r, "day", t // 1440))
        hour = int(getattr(r, "hour", (t % 1440) // 60))
        dow = int(getattr(r, "dow", day % 7))
        pn = self.user_n.get(user, 0)
        ps = self.user_s.get(user, 0)

        ao = self.all_times.get(cell, [])
        last15_cell = bisect.bisect_left(ao, t) - bisect.bisect_left(ao, t - 15)

        avg_hist = 0.0
        if self.hourly_counts is not None and day > 0:
            avg_hist = float(self.hourly_counts[:day, hour, cell].sum() / day)

        f: dict[str, Any] = dict(
            order_id=int(r.order_id),
            user_id=user,
            day=day,
            hour=hour,
            day_of_week=dow,
            is_weekend=int(dow >= 5),
            is_peak_hour=int(hour in PEAK_HOURS),
            grid_cell_id=cell,
            grid_row=cell // GRID,
            grid_col=cell % GRID,
            zone_type=str(zone[cell]),
            order_value=int(r.value),
            n_items=int(r.n_items),
            orders_in_cell_last_15min=int(last15_cell),
            avg_orders_in_cell_this_hour=round(avg_hist, 3),
            user_past_order_count=int(pn),
            user_small_order_ratio=round(ps / pn, 3) if pn else 0.0,
        )
        for metres, k in RADII.items():
            cnt15 = 0
            for nb in neighbours(cell, k):
                st = self.small_times.get(nb, [])
                cnt15 += bisect.bisect_left(st, t) - bisect.bisect_left(st, t - 15)
            f[f"small_orders_{metres}m_last_15min"] = int(cnt15)
        return f


def causal_candidates(
    index: EventIndex,
    cell: int,
    t: float,
    user: int,
    radius_m: int,
    wait_minutes: int,
    arrived_max_t: float,
) -> list[dict[str, Any]]:
    """Candidates that have already arrived (t_partner <= arrived_max_t) and are in the window."""
    k = RADII[int(radius_m)]
    found: list[dict[str, Any]] = []
    r0, c0 = divmod(cell, GRID)
    horizon = t + wait_minutes
    for nb in neighbours(cell, k):
        st = index.small_times.get(nb, [])
        su = index.small_users.get(nb, [])
        sv = index.small_values.get(nb, [])
        so = index.small_ids.get(nb, [])
        i = bisect.bisect_right(st, t)
        while i < len(st) and st[i] <= horizon and st[i] <= arrived_max_t:
            if su[i] != user:
                r1, c1 = divmod(nb, GRID)
                found.append(
                    {
                        "order_id": int(so[i]),
                        "user": int(su[i]),
                        "t": float(st[i]),
                        "value": float(sv[i]),
                        "cell": int(nb),
                        "waited_minutes": float(st[i] - t),
                        "grid_distance": int(max(abs(r1 - r0), abs(c1 - c0))),
                    }
                )
            i += 1
    found.sort(key=lambda x: x["t"])
    return found


def first_partner_offline(
    events: pd.DataFrame, cell: int, t: float, user: int, k: int, maxw: int = 15
) -> tuple[float, float, int]:
    """Notebook-style lookahead partner (for labels / offline impact only)."""
    small = events[events.small == 1]
    s_times = {c: g.t.values for c, g in small.groupby("cell")}
    s_users = {c: g.user.values for c, g in small.groupby("cell")}
    s_vals = {c: g.value.values for c, g in small.groupby("cell")}
    best = (np.inf, np.nan, 0)
    r0, c0 = divmod(cell, GRID)
    empty = np.array([])
    for nb in neighbours(cell, k):
        st = s_times.get(nb, empty)
        su = s_users.get(nb, empty)
        sv = s_vals.get(nb, empty)
        i = bisect.bisect_right(st, t)
        while i < len(st) and st[i] - t <= maxw:
            if su[i] != user:
                if st[i] - t < best[0]:
                    r1, c1 = divmod(nb, GRID)
                    best = (float(st[i] - t), float(sv[i]), int(max(abs(r1 - r0), abs(c1 - c0))))
                break
            i += 1
    return best
