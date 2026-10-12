from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from backend.app.paths import CATALOG_CSV, EVENTS_CSV, TRAINING_CSV

DATASETS = {
    "catalog": {
        "path": CATALOG_CSV,
        "kind": "Original catalogue data",
        "description": "Cleaned BlinkIT/BigMart grocery items (price averaged per item id).",
    },
    "events": {
        "path": EVENTS_CSV,
        "kind": "Simulated order-event data",
        "description": "Seed-42 simulated orders. t is simulated minutes, not wall-clock time.",
    },
    "training": {
        "path": TRAINING_CSV,
        "kind": "Engineered ML training data",
        "description": "15 wait/radius scenario rows per small order. Target: partner_found.",
    },
}


def _summary(name: str, meta: dict[str, Any], df: pd.DataFrame) -> dict[str, Any]:
    sample = df.head(12).where(pd.notnull(df.head(12)), None)
    numeric = df.select_dtypes(include="number")
    missing = df.isna().sum().to_dict()
    out: dict[str, Any] = {
        "id": name,
        "kind": meta["kind"],
        "description": meta["description"],
        "rows": int(len(df)),
        "columns": [{"name": c, "dtype": str(df[c].dtype)} for c in df.columns],
        "missing": {k: int(v) for k, v in missing.items()},
        "sample": sample.to_dict(orient="records"),
        "numeric_summary": numeric.describe().round(3).to_dict() if len(numeric.columns) else {},
    }
    if "order_id" in df.columns:
        out["order_id_min"] = int(df.order_id.min())
        out["order_id_max"] = int(df.order_id.max())
        out["unique_orders"] = int(df.order_id.nunique())
    if "t" in df.columns:
        out["t_min"] = float(df.t.min())
        out["t_max"] = float(df.t.max())
    if "cell" in df.columns:
        out["unique_cells"] = int(df.cell.nunique())
    if "zone_type" in df.columns:
        out["zones"] = df.zone_type.value_counts().to_dict()
    if "partner_found" in df.columns:
        out["target_rate"] = float(df.partner_found.mean())
        out["target_counts"] = df.partner_found.value_counts().to_dict()
    if {"wait_minutes", "radius_m"} <= set(df.columns):
        out["scenarios"] = (
            df.groupby(["wait_minutes", "radius_m"]).size().reset_index(name="n").to_dict(orient="records")
        )
    return out


def list_summaries() -> list[dict[str, Any]]:
    rows = []
    for name, meta in DATASETS.items():
        path: Path = meta["path"]
        if not path.exists():
            rows.append({"id": name, "kind": meta["kind"], "missing": True, "path": str(path)})
            continue
        df = pd.read_csv(path)
        rows.append(_summary(name, meta, df))
    return rows


def preview(name: str, limit: int = 50) -> dict[str, Any]:
    if name not in DATASETS:
        raise KeyError(name)
    meta = DATASETS[name]
    path: Path = meta["path"]
    if not path.exists():
        raise FileNotFoundError(str(path))
    df = pd.read_csv(path)
    return _summary(name, meta, df.head(limit) if False else df)
