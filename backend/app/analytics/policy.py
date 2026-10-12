"""Offline policy comparison matching the notebook (test small orders only)."""

from __future__ import annotations

import bisect
from typing import Any

import numpy as np
import pandas as pd

from backend.app.ml.constants import DETOUR_MIN, FEE, GRID, LAM, MAXW, RADII, THRESHOLD, WAITS
from backend.app.ml.simulate import neighbours
from backend.app.paths import EVENTS_CSV, POLICY_CSV, TRAINING_CSV, ensure_dirs
from backend.app.pooling.engine import fee_saving as fee_saving_scalar


def fee_saving(v, pv, fee: float = FEE, threshold: float = THRESHOLD):
    comb = np.asarray(v) + np.asarray(pv)
    pv = np.asarray(pv)
    return np.where(comb >= threshold, fee, fee * pv / np.maximum(comb, 1e-9))


def _partner_records(events: pd.DataFrame) -> dict[int, list[tuple[float, float, int]]]:
    small = events[events.small == 1]
    s_times = {c: g.t.values for c, g in small.groupby("cell")}
    s_users = {c: g.user.values for c, g in small.groupby("cell")}
    s_vals = {c: g.value.values for c, g in small.groupby("cell")}
    empty = np.array([])

    def first_partner(row, k):
        best = (np.inf, np.nan, 0)
        r0, c0 = divmod(int(row.cell), GRID)
        for cell in neighbours(int(row.cell), k):
            st = s_times.get(cell, empty)
            su = s_users.get(cell, empty)
            sv = s_vals.get(cell, empty)
            i = bisect.bisect_right(st, row.t)
            while i < len(st) and st[i] - row.t <= MAXW:
                if su[i] != row.user:
                    if st[i] - row.t < best[0]:
                        r1, c1 = divmod(cell, GRID)
                        best = (st[i] - row.t, sv[i], max(abs(r1 - r0), abs(c1 - c0)))
                    break
                i += 1
        return best

    rec = {}
    for r in events[events.small == 1].itertuples(index=False):
        rec[int(r.order_id)] = [first_partner(r, k) for k in (0, 1, 2)]
    return rec


def evaluate_policies(
    events: pd.DataFrame | None = None,
    train_df: pd.DataFrame | None = None,
    probabilities: pd.Series | None = None,
    lam: float = LAM,
    detour: float = DETOUR_MIN,
    fee: float = FEE,
) -> pd.DataFrame:
    ensure_dirs()
    if events is None:
        events = pd.read_csv(EVENTS_CSV)
    if train_df is None:
        train_df = pd.read_csv(TRAINING_CSV)

    rec = _partner_records(events)
    train = train_df[train_df.split == "train"]
    test = train_df[train_df.split == "test"].copy()
    ids_train = set(train.order_id)
    ids_test = set(test.order_id)
    foc = events[(events.small == 1) & events.order_id.isin(ids_train | ids_test)].set_index("order_id")
    kof = {300: 0, 600: 1, 900: 2}
    radii = [300, 600, 900]

    tr = [
        (w, r, rec[o][kof[r]][0] + detour * rec[o][kof[r]][2])
        for o in ids_train
        if o in rec
        for r in radii
        for w in WAITS
        if rec[o][kof[r]][0] <= w
    ]
    mean_dly = pd.DataFrame(tr, columns=["w", "r", "d"]).groupby(["w", "r"]).d.mean()
    pv_train = foc.loc[list(ids_train.intersection(set(foc.index))), "value"].values

    if probabilities is not None:
        test = test.copy()
        test["p"] = probabilities
    elif "p" not in test.columns:
        test["p"] = np.nan

    T = test.pivot_table(index="order_id", columns=["radius_m", "wait_minutes"], values="p")
    oid = T.index.values
    vals = foc.loc[oid, "value"].values
    combos = [(w, r) for r in radii for w in WAITS]

    sav = np.zeros((len(oid), len(combos)))
    delay = np.zeros_like(sav)
    found = np.zeros_like(sav)
    for j, (w, r) in enumerate(combos):
        k = kof[r]
        ttp = np.array([rec[o][k][0] for o in oid])
        pv = np.array([rec[o][k][1] for o in oid])
        dd = np.array([rec[o][k][2] for o in oid])
        f = ttp <= w
        found[:, j] = f
        delay[:, j] = np.where(f, ttp + detour * dd, w)
        sav[:, j] = np.where(f, fee_saving(vals, np.nan_to_num(pv), fee, THRESHOLD), 0)

    def outcome(choice):
        n = len(oid)
        idx = np.arange(n)
        m = choice >= 0
        c = np.where(m, choice, 0)
        return np.where(m, sav[idx, c], 0), np.where(m, delay[idx, c], 0), np.where(m, found[idx, c], 0), m

    def summarise(name, choice):
        s, d, f, m = outcome(choice)
        return dict(
            Policy=name,
            pooled_pct=100 * f.mean(),
            avg_saving=s.mean(),
            avg_delay=d.mean(),
            wasted_wait_pct=100 * (m & (f == 0)).mean(),
            net=s.mean() - lam * d.mean(),
            orders=int(len(oid)),
            fee=fee,
            lam=lam,
            detour_min=detour,
        )

    rows = [summarise("No pooling", np.full(len(oid), -1))]
    for w, r in [(5, 300), (10, 600), (15, 900)]:
        rows.append(summarise(f"Fixed {w}min/{r}m", np.full(len(oid), combos.index((w, r)))))

    if test["p"].notna().any():
        P = np.column_stack([T[(r, w)].values for (w, r) in combos])
        es_map = {v: fee_saving(np.full(len(pv_train), v), pv_train, fee).mean() for v in np.unique(vals)}
        Es = np.array([es_map[v] for v in vals])[:, None] * P
        MT = np.array([mean_dly.get((w, r), w) for (w, r) in combos])[None, :]
        ED = P * MT + (1 - P) * np.array([w for (w, r) in combos])[None, :]
        score = Es - lam * ED
        smart = np.where(score.max(axis=1) > 0, score.argmax(axis=1), -1)
        rows.append(summarise(f"ML-guided (lambda={lam})", smart))
    else:
        rows.append(
            {
                "Policy": "ML-guided (probabilities unavailable)",
                "pooled_pct": np.nan,
                "avg_saving": np.nan,
                "avg_delay": np.nan,
                "wasted_wait_pct": np.nan,
                "net": np.nan,
                "orders": int(len(oid)),
                "fee": fee,
                "lam": lam,
                "detour_min": detour,
            }
        )

    out = pd.DataFrame(rows).round(4)
    out.to_csv(POLICY_CSV, index=False)
    return out


def live_impact(records: list[dict[str, Any]], fee: float = FEE, lam: float = LAM) -> dict[str, Any]:
    if not records:
        return {
            "orders": 0,
            "pooled": 0,
            "dispatched_solo": 0,
            "waited_no_match": 0,
            "pooling_rate": 0.0,
            "avg_wait": 0.0,
            "avg_delay": 0.0,
            "avg_saving": 0.0,
            "estimated_savings_total": 0.0,
            "fee": fee,
            "lam": lam,
            "note": "No simulation records yet. Start the event player to accumulate live metrics.",
        }
    n = len(records)
    pooled = sum(1 for r in records if r.get("action") == "POOL")
    solo = sum(1 for r in records if r.get("action") == "DISPATCH")
    wasted = sum(1 for r in records if r.get("waited_without_match"))
    waits = [float(r.get("elapsed_wait") or 0) for r in records]
    delays = [float(r.get("delay") or r.get("elapsed_wait") or 0) for r in records]
    savings = [float(r.get("saving") or 0) for r in records]
    return {
        "orders": n,
        "pooled": pooled,
        "dispatched_solo": solo,
        "waited_no_match": wasted,
        "pooling_rate": pooled / n if n else 0.0,
        "avg_wait": float(np.mean(waits)) if waits else 0.0,
        "avg_delay": float(np.mean(delays)) if delays else 0.0,
        "avg_saving": float(np.mean(savings)) if savings else 0.0,
        "estimated_savings_total": float(np.sum(savings)),
        "fee": fee,
        "lam": lam,
        "note": "Live metrics come from played simulation decisions. Savings use the notebook fee formula and are simulated rupees, not commercial P&L.",
    }
