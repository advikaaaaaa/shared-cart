"""Regenerate catalogue, events, training rows, model, and evaluation files from the notebook logic."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.ml.simulate import add_engineered_features, generate_core_datasets
from backend.app.ml.train import train_and_export
from backend.app.paths import DATA_DIR, EVENTS_CSV, MODEL_PKL, TRAINING_CSV, ensure_dirs


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Rebuild CSVs even if they exist")
    parser.add_argument("--skip-train", action="store_true")
    parser.add_argument("--skip-policy", action="store_true")
    parser.add_argument(
        "--full",
        action="store_true",
        help="Notebook-scale simulation (65 days × ~1200 orders). Slow; use for the full capstone rebuild.",
    )
    args = parser.parse_args()
    ensure_dirs()

    if args.full:
        scale = {}
        print("Scale: full notebook constants (65 days, 1200 orders/day, 4000 users).")
    else:
        # Same seed and process as the notebook, reduced volume so local training is practical.
        scale = dict(n_users=1000, total_days=20, warmup_days=3, train_last_day=13, orders_per_day=400)
        print("Scale: lite demo (20 days, 400 orders/day). Pass --full for notebook volume.")

    print("Generating / loading core datasets...")
    payload = generate_core_datasets(force=args.force, **scale)
    df = payload["train_df"]
    if "hour_sin" not in df.columns:
        df, cap = add_engineered_features(df)
        payload["busy_cap"] = cap
        df.to_csv(TRAINING_CSV, index=False)
    else:
        cap = payload.get("busy_cap")
        if cap is None:
            cap = float(df.loc[df.split == "train", "busy_ratio"].quantile(0.99))
    import json

    scale_info = payload.get("scale") or {
        "note": "Loaded existing CSVs; scale matches whatever was last generated."
    }
    scale_info["lite"] = not args.full
    (DATA_DIR / "scale.json").write_text(json.dumps(scale_info, indent=2), encoding="utf-8")
    print("events", EVENTS_CSV, "rows", len(payload["orders"]))
    print("training", TRAINING_CSV, "rows", len(df))
    print("busy_ratio cap", cap)

    if not args.skip_train or not MODEL_PKL.exists():
        print("Training models (this can take a few minutes)...")
        out = train_and_export(df, busy_cap=cap)
        print("Best model:", out["best"])
        print(out["results"].to_string(index=False))
        import joblib
        from backend.app.ml.constants import FINAL_FEATURES

        pipe = joblib.load(MODEL_PKL)
        sample = df[df.split == "test"][FINAL_FEATURES].head(1)
        p = pipe.predict_proba(sample)[0, 1]
        print("Smoke-test probability on first test row:", round(float(p), 4))

        if not args.skip_policy:
            print("Computing offline policy comparison...")
            from backend.app.analytics.policy import evaluate_policies
            from backend.app.ml.constants import FINAL_FEATURES as FEATS

            dfp = df.copy()
            dfp["p"] = 0.0
            mask = dfp.split == "test"
            dfp.loc[mask, "p"] = pipe.predict_proba(dfp.loc[mask, FEATS])[:, 1]
            table = evaluate_policies(payload["orders"], dfp)
            print(table.to_string(index=False))
    print("Done.")


if __name__ == "__main__":
    main()
