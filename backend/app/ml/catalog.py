from __future__ import annotations

import pandas as pd

from backend.app.ml.constants import GRID, SEED
from backend.app.paths import BIGMART_CSV, CATALOG_CSV


def load_or_build_catalog() -> pd.DataFrame:
    if CATALOG_CSV.exists():
        return pd.read_csv(CATALOG_CSV)
    if not BIGMART_CSV.exists():
        raise FileNotFoundError(
            f"Neither {CATALOG_CSV} nor source file {BIGMART_CSV} was found. "
            "Place the BlinkIT/BigMart grocery table at data/source/bigmart_train.csv."
        )
    raw = pd.read_csv(BIGMART_CSV)
    raw.columns = [c.strip() for c in raw.columns]
    catalog = (
        raw.groupby("Item_Identifier")
        .agg(item_type=("Item_Type", "first"), item_price=("Item_MRP", "mean"))
        .reset_index()
        .rename(columns={"Item_Identifier": "item_id"})
    )
    catalog["item_price"] = catalog["item_price"].round(0).astype(int)
    catalog["is_small_item"] = (catalog["item_price"] < 75).astype(int)
    catalog["price_band"] = (
        pd.cut(
            catalog["item_price"],
            [0, 50, 100, 150, 1000],
            labels=["<50", "50-100", "100-150", "150+"],
        ).astype(str)
    )
    CATALOG_CSV.parent.mkdir(parents=True, exist_ok=True)
    catalog.to_csv(CATALOG_CSV, index=False)
    return catalog


def build_zone_map(rng=None) -> tuple[object, object]:
    import numpy as np

    rng = rng if rng is not None else np.random.default_rng(SEED)
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
    return zone, rng


def zone_directory(zone) -> list[dict]:
    rows = []
    for cell, z in enumerate(zone):
        r, c = divmod(cell, GRID)
        rows.append(
            {
                "cell": int(cell),
                "grid_row": int(r),
                "grid_col": int(c),
                "zone_type": str(z),
                "label": f"Cell {r}-{c} · {z.replace('_', ' ')}",
            }
        )
    return rows
