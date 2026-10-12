from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

import joblib
import pandas as pd

from backend.app.ml.constants import FINAL_FEATURES
from backend.app.ml.simulate import engineer_row
from backend.app.paths import MODEL_META, MODEL_PKL


class ModelNotAvailable(RuntimeError):
    pass


@lru_cache(maxsize=1)
def load_meta() -> dict[str, Any]:
    if not MODEL_META.exists():
        raise ModelNotAvailable(f"Missing {MODEL_META}. Run scripts/generate_artefacts.py")
    return json.loads(MODEL_META.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def load_pipeline():
    if not MODEL_PKL.exists():
        raise ModelNotAvailable(f"Missing {MODEL_PKL}. Run scripts/generate_artefacts.py")
    return joblib.load(MODEL_PKL)


def busy_cap() -> float:
    return float(load_meta().get("busy_ratio_cap") or 10.44)


def required_features() -> list[str]:
    return list(load_meta().get("features") or FINAL_FEATURES)


def predict_proba_row(feature_row: dict[str, Any]) -> dict[str, Any]:
    feats = required_features()
    missing = [c for c in feats if c not in feature_row or feature_row[c] is None]
    if missing:
        raise ValueError(f"Missing model features: {missing}")
    X = pd.DataFrame([{c: feature_row[c] for c in feats}])
    pipe = load_pipeline()
    if not hasattr(pipe, "predict_proba"):
        raise ModelNotAvailable("Loaded artefact does not support predict_proba")
    p = float(pipe.predict_proba(X)[0, 1])
    y = int(p >= 0.5)
    return {
        "probability": p,
        "predicted_class": y,
        "predicted_label": "partner_likely" if y else "partner_unlikely",
        "features_used": feats,
        "model_name": load_meta().get("best_model"),
    }


def predict_from_base(
    base_features: dict[str, Any], wait_minutes: int, radius_m: int
) -> tuple[dict[str, Any], dict[str, Any]]:
    row = engineer_row(base_features, wait_minutes, radius_m, busy_cap())
    result = predict_proba_row(row)
    return row, result
