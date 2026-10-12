from __future__ import annotations

import json
from typing import Any

import pandas as pd
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from backend.app.analytics.datasets import list_summaries, preview
import numpy as np

from backend.app.ml.catalog import load_or_build_catalog, zone_directory
from backend.app.ml.simulate import build_zones
from backend.app.ml.constants import FEE, LAM, DETOUR_MIN, MAXW, RADIUS_LIST, THRESHOLD, WAITS
from backend.app.ml.predict import ModelNotAvailable, load_meta, predict_from_base
from backend.app.paths import (
    CALIBRATION_CSV,
    CONFUSION_CSV,
    FEATURE_IMPORTANCE_CSV,
    MODEL_COMPARISON,
    POLICY_CSV,
    ZONE_AUC_CSV,
)
from backend.app.simulation.runtime import _public_order, get_runtime

router = APIRouter()


class CheckoutItem(BaseModel):
    item_id: str
    item_type: str | None = None
    unit_price: int
    quantity: int = Field(ge=1, le=20)


class CheckoutBody(BaseModel):
    cell: int = Field(ge=0, le=99)
    customer_name: str = "Guest"
    items: list[CheckoutItem]


class PredictionBody(BaseModel):
    order_id: int
    wait_minutes: int
    radius_m: int


class SimSpeedBody(BaseModel):
    speed: float = Field(gt=0, le=240)


@router.get("/health")
def health() -> dict[str, Any]:
    model_ok = True
    model_error = None
    meta: dict[str, Any] = {}
    try:
        meta = load_meta()
    except ModelNotAvailable as exc:
        model_ok = False
        model_error = str(exc)
    if model_ok:
        try:
            from backend.app.ml.predict import load_pipeline

            load_pipeline()
        except ModelNotAvailable as exc:
            model_ok = False
            model_error = str(exc)
    return {
        "ok": True,
        "product": "SharedCart",
        "tagline": "SharedCart — Smarter Food Delivery Through Intelligent Order Pooling",
        "model_loaded": model_ok,
        "model_error": model_error,
        "model_name": meta.get("best_model"),
        "simulation": True,
    }


@router.get("/catalog")
def catalog(q: str | None = None, category: str | None = None, limit: int = 200):
    df = load_or_build_catalog()
    if q:
        ql = q.lower()
        df = df[df.item_id.str.lower().str.contains(ql) | df.item_type.str.lower().str.contains(ql)]
    if category and category != "all":
        df = df[df.item_type == category]
    elif not q:
        mixed = df.copy()
        mixed["_r"] = mixed.groupby("item_type").cumcount()
        df = mixed.sort_values(["_r", "item_type"]).drop(columns="_r")
    categories = sorted(load_or_build_catalog().item_type.unique().tolist())
    zones = zone_directory(build_zones(np.random.default_rng(42)))
    return {
        "disclaimer": "Sample grocery catalogue from the BlinkIT/BigMart item table used in the capstone simulation. These are not live restaurant menu items.",
        "categories": categories,
        "zones": zones,
        "count": int(len(df)),
        "items": df.head(limit).to_dict(orient="records"),
    }


@router.get("/simulation/status")
def sim_status():
    return get_runtime().status()


@router.post("/simulation/start")
def sim_start():
    return get_runtime().start()


@router.post("/simulation/pause")
def sim_pause():
    return get_runtime().pause()


@router.post("/simulation/resume")
def sim_resume():
    return get_runtime().resume()


@router.post("/simulation/reset")
def sim_reset(start_day: int = 7):
    return get_runtime().reset(persist_customers=True, start_day=start_day)


@router.post("/simulation/step")
def sim_step(n: int = Query(default=1, ge=1, le=500)):
    return get_runtime().step(n)


@router.post("/simulation/speed")
def sim_speed(body: SimSpeedBody):
    return get_runtime().set_speed(body.speed)


@router.get("/orders")
def list_orders(source: str | None = None, status: str | None = None, q: str | None = None):
    return {"orders": get_runtime().list_orders(source=source, q=q, status=status)}


@router.post("/orders")
def create_order(body: CheckoutBody):
    if not body.items:
        raise HTTPException(400, "Cart is empty")
    order = get_runtime().place_customer_order(
        [i.model_dump() for i in body.items], body.cell, body.customer_name
    )
    return {"order": order, "message": "Simulated checkout only — no payment was collected."}


@router.get("/orders/{order_id}")
def get_order(order_id: int):
    order = get_runtime().get_order(order_id)
    if not order:
        raise HTTPException(404, "Order not found")
    return {"order": _public_order(order) if "base_features" in order or "history" in order else order}


@router.get("/orders/{order_id}/tracking")
def tracking(order_id: int):
    payload = get_runtime().tracking(order_id)
    if not payload:
        raise HTTPException(404, "Order not found")
    return payload


@router.post("/predictions")
def predictions(body: PredictionBody):
    if body.wait_minutes not in WAITS:
        raise HTTPException(400, f"wait_minutes must be one of {WAITS}")
    if body.radius_m not in RADIUS_LIST:
        raise HTTPException(400, f"radius_m must be one of {RADIUS_LIST}")
    try:
        return get_runtime().run_prediction(body.order_id, body.wait_minutes, body.radius_m)
    except KeyError:
        raise HTTPException(404, "Order is not in the current simulation. Step the player until it appears, or pick an active order.")
    except ModelNotAvailable as exc:
        raise HTTPException(503, str(exc))
    except ValueError as exc:
        raise HTTPException(400, str(exc))


@router.get("/ops/dashboard")
def dashboard():
    return get_runtime().dashboard()


@router.get("/models/metrics")
def model_metrics():
    def read(path):
        if not path.exists():
            return None
        return pd.read_csv(path).to_dict(orient="records")

    try:
        meta = load_meta()
    except ModelNotAvailable as exc:
        meta = {"error": str(exc)}
    return {
        "simulated_data": True,
        "disclaimer": "Metrics are from the simulated capstone dataset. They are not live operational performance.",
        "meta": meta,
        "comparison": read(MODEL_COMPARISON),
        "confusion": read(CONFUSION_CSV),
        "calibration": read(CALIBRATION_CSV),
        "importance": read(FEATURE_IMPORTANCE_CSV),
        "zone_auc": read(ZONE_AUC_CSV),
        "constants": {
            "waits": WAITS,
            "radii": RADIUS_LIST,
            "threshold": THRESHOLD,
            "fee": FEE,
            "lambda": LAM,
            "detour_min": DETOUR_MIN,
            "max_wait": MAXW,
        },
    }


class ImpactBody(BaseModel):
    fee: float = Field(gt=0, le=500, default=FEE)
    lam: float = Field(gt=0, le=50, default=LAM)
    detour: float = Field(ge=0, le=30, default=DETOUR_MIN)


@router.get("/analytics/impact")
def impact():
    live = get_runtime().dashboard()["impact"]
    offline = None
    if POLICY_CSV.exists():
        offline = pd.read_csv(POLICY_CSV).to_dict(orient="records")
    return {
        "assumptions": {
            "delivery_fee_rs": FEE,
            "free_delivery_threshold_rs": THRESHOLD,
            "delay_cost_rs_per_min": LAM,
            "detour_min_per_grid_cell": DETOUR_MIN,
            "max_wait_minutes": MAXW,
            "note": "These are notebook assumptions, not empirically optimal values. Figures are simulated rupees.",
        },
        "offline_test_policies": offline,
        "live_simulation": live,
    }


@router.post("/analytics/impact")
def impact_recompute(body: ImpactBody):
    from backend.app.analytics.policy import evaluate_policies
    from backend.app.ml.constants import FINAL_FEATURES as FEATS
    from backend.app.ml.predict import load_pipeline
    from backend.app.paths import EVENTS_CSV, TRAINING_CSV

    if not EVENTS_CSV.exists() or not TRAINING_CSV.exists():
        raise HTTPException(404, "Datasets missing. Run scripts/generate_artefacts.py")
    events = pd.read_csv(EVENTS_CSV)
    dfp = pd.read_csv(TRAINING_CSV)
    try:
        pipe = load_pipeline()
        mask = dfp.split == "test"
        dfp["p"] = 0.0
        dfp.loc[mask, "p"] = pipe.predict_proba(dfp.loc[mask, FEATS])[:, 1]
    except ModelNotAvailable as exc:
        raise HTTPException(503, str(exc))
    table = evaluate_policies(events, dfp, lam=body.lam, detour=body.detour, fee=body.fee)
    live = get_runtime().dashboard()["impact"]
    return {
        "assumptions": {
            "delivery_fee_rs": body.fee,
            "free_delivery_threshold_rs": THRESHOLD,
            "delay_cost_rs_per_min": body.lam,
            "detour_min_per_grid_cell": body.detour,
            "max_wait_minutes": MAXW,
            "note": "Recomputed on the held-out test orders with your fee/λ/detour. Simulated rupees only.",
        },
        "offline_test_policies": table.to_dict(orient="records"),
        "live_simulation": live,
    }


@router.get("/datasets/summary")
def datasets_summary():
    return {"datasets": list_summaries()}


@router.get("/datasets/{name}")
def dataset_detail(name: str):
    try:
        return preview(name)
    except KeyError:
        raise HTTPException(404, "Unknown dataset")
    except FileNotFoundError:
        raise HTTPException(404, "Dataset file is not on disk. Run scripts/generate_artefacts.py")
