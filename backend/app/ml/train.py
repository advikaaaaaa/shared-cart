"""Train the notebook models once and persist evaluation artefacts."""

from __future__ import annotations

import json
import time
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    log_loss,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from backend.app.ml.constants import FINAL_FEATURES, ORIGINAL_FEATURES, RADIUS_LIST, WAITS
from backend.app.ml.simulate import add_engineered_features
from backend.app.paths import (
    CALIBRATION_CSV,
    CONFUSION_CSV,
    FEATURE_IMPORTANCE_CSV,
    MODEL_COMPARISON,
    MODEL_META,
    MODEL_PKL,
    TRAINING_CSV,
    ZONE_AUC_CSV,
    ensure_dirs,
)

TARGET = "partner_found"


def make_pipe(model, feats: list[str], scale: bool = False) -> Pipeline:
    cat = [c for c in feats if c == "zone_type"]
    num = [c for c in feats if c != "zone_type"]
    pre = ColumnTransformer(
        [
            ("cat", OneHotEncoder(handle_unknown="ignore"), cat),
            ("num", StandardScaler() if scale else "passthrough", num),
        ]
    )
    return Pipeline([("pre", pre), ("model", model)])


def get_models(feats: list[str]) -> dict[str, Pipeline]:
    models: dict[str, Pipeline] = {
        "Logistic Regression": make_pipe(
            LogisticRegression(max_iter=2000), feats, scale=True
        ),
        "Random Forest": make_pipe(
            RandomForestClassifier(
                n_estimators=100,
                max_depth=12,
                min_samples_leaf=20,
                n_jobs=-1,
                random_state=42,
            ),
            feats,
        ),
    }
    try:
        from xgboost import XGBClassifier

        models["XGBoost"] = make_pipe(
            XGBClassifier(
                n_estimators=200,
                max_depth=6,
                learning_rate=0.1,
                subsample=0.8,
                colsample_bytree=0.8,
                eval_metric="logloss",
                random_state=42,
                n_jobs=-1,
            ),
            feats,
        )
    except Exception as exc:  # pragma: no cover
        print("XGBoost unavailable:", exc)
    return models


def score_row(name: str, fset: str, y_true, p) -> dict[str, Any]:
    pred = (p >= 0.5).astype(int)
    return {
        "Model": name,
        "Features": fset,
        "Accuracy": accuracy_score(y_true, pred),
        "Precision": precision_score(y_true, pred, zero_division=0),
        "Recall": recall_score(y_true, pred, zero_division=0),
        "F1": f1_score(y_true, pred, zero_division=0),
        "ROC-AUC": roc_auc_score(y_true, p),
        "Log-loss": log_loss(y_true, np.clip(p, 1e-6, 1 - 1e-6)),
        "Brier": brier_score_loss(y_true, p),
    }


def train_and_export(df: pd.DataFrame | None = None, busy_cap: float | None = None) -> dict[str, Any]:
    ensure_dirs()
    if df is None:
        df = pd.read_csv(TRAINING_CSV)
    if "hour_sin" not in df.columns:
        df, busy_cap = add_engineered_features(df, busy_cap)
    elif busy_cap is None:
        busy_cap = float(df.loc[df.split == "train", "busy_ratio"].max())

    train = df[df.split == "train"]
    test = df[df.split == "test"]
    y_train, y_test = train[TARGET], test[TARGET]

    results, fitted, probs = [], {}, {}
    results.append(score_row("Majority class", "-", y_test, np.full(len(y_test), y_train.mean())))
    lookup = train.groupby(["wait_minutes", "radius_m"])[TARGET].mean()
    p_lookup = test.set_index(["wait_minutes", "radius_m"]).index.map(lookup).to_numpy(dtype=float)
    results.append(score_row("Fixed-rule lookup (wait, radius only)", "wait, radius", y_test, p_lookup))
    probs[("Fixed-rule lookup", "-")] = p_lookup

    for fset, feats in [("Original (18)", ORIGINAL_FEATURES), ("Final (23)", FINAL_FEATURES)]:
        for name, pipe in get_models(feats).items():
            t0 = time.time()
            pipe.fit(train[feats], y_train)
            p = pipe.predict_proba(test[feats])[:, 1]
            r = score_row(name, fset, y_test, p)
            r["Train sec"] = round(time.time() - t0, 1)
            results.append(r)
            fitted[(name, fset)] = pipe
            probs[(name, fset)] = p
            print(f"done: {name:20s} {fset:14s} AUC={r['ROC-AUC']:.4f}  ({r['Train sec']}s)")

    res = pd.DataFrame(results).round(4)
    res.to_csv(MODEL_COMPARISON, index=False)

    best = max(
        [k for k in fitted if k[1].startswith("Final")],
        key=lambda k: roc_auc_score(y_test, probs[k]),
    )
    best_pipe = fitted[best]
    joblib.dump(best_pipe, MODEL_PKL)

    cm_rows = []
    for (name, fset), p in probs.items():
        if name == "Fixed-rule lookup":
            continue
        pred = (p >= 0.5).astype(int)
        tn, fp, fn, tp = confusion_matrix(y_test, pred).ravel()
        cm_rows.append(
            {"Model": name, "Features": fset, "tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)}
        )
    pd.DataFrame(cm_rows).to_csv(CONFUSION_CSV, index=False)

    from sklearn.calibration import calibration_curve

    cal_rows = []
    for key in [best, ("Logistic Regression", "Final (23)")]:
        if key not in probs:
            continue
        fp, mp = calibration_curve(y_test, probs[key], n_bins=10)
        for m, f in zip(mp, fp):
            cal_rows.append({"model": key[0], "pred_mean": float(m), "frac_positive": float(f)})
    pd.DataFrame(cal_rows).to_csv(CALIBRATION_CSV, index=False)

    try:
        from sklearn.inspection import permutation_importance

        samp = test.sample(min(8000, len(test)), random_state=42)
        pi = permutation_importance(
            best_pipe,
            samp[FINAL_FEATURES],
            samp[TARGET],
            scoring="roc_auc",
            n_repeats=2,
            random_state=42,
            n_jobs=-1,
        )
        imp = (
            pd.Series(pi.importances_mean, index=FINAL_FEATURES)
            .sort_values(ascending=False)
            .rename("auc_drop")
            .reset_index()
            .rename(columns={"index": "feature"})
        )
        imp.to_csv(FEATURE_IMPORTANCE_CSV, index=False)
    except Exception as exc:
        print("permutation importance skipped:", exc)

    tmp = test.copy()
    tmp["p"] = probs[best]
    zone_auc = (
        tmp.groupby("zone_type")
        .apply(lambda g: roc_auc_score(g[TARGET], g["p"]), include_groups=False)
        .rename("roc_auc")
        .reset_index()
    )
    zone_auc.to_csv(ZONE_AUC_CSV, index=False)

    import sklearn

    meta = {
        "features": FINAL_FEATURES,
        "original_features": ORIGINAL_FEATURES,
        "waits": WAITS,
        "radii": RADIUS_LIST,
        "best_model": best[0],
        "feature_set": best[1],
        "target": TARGET,
        "busy_ratio_cap": float(busy_cap) if busy_cap is not None else None,
        "sklearn_version": sklearn.__version__,
        "n_train": int(len(train)),
        "n_test": int(len(test)),
        "positive_rate_train": float(y_train.mean()),
        "positive_rate_test": float(y_test.mean()),
        "test_roc_auc": float(roc_auc_score(y_test, probs[best])),
        "notes": (
            "Dataset is simulated. Test metrics use scenario rows split by day. "
            "Do not interpret as live restaurant performance."
        ),
    }
    MODEL_META.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return {"results": res, "best": best, "meta": meta, "busy_cap": busy_cap}
