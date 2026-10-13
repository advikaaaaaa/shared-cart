from __future__ import annotations

import json
import os
from typing import Any

import pandas as pd
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field

from backend.app.analytics.datasets import list_summaries, preview
import numpy as np

from backend.app.auth import (
    ADMIN_COOKIE,
    ADMIN_SESSION_SECONDS,
    create_admin_session,
    credentials_configured,
    require_admin,
    valid_admin_session,
    verify_credentials,
)
from backend.app.order_access import valid_order_access_key
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
from backend.app.simulation.runtime import DEFAULT_CHECKOUT_CELL, _public_order, get_runtime

router = APIRouter()


class CheckoutItem(BaseModel):
    item_id: str
    item_type: str | None = None
    unit_price: int = Field(gt=0)
    quantity: int = Field(ge=1, le=20)


class CheckoutBody(BaseModel):
    cell: int = Field(default=DEFAULT_CHECKOUT_CELL, ge=0, le=99)
    customer_name: str = Field(default="Guest", max_length=120)
    items: list[CheckoutItem] = Field(max_length=100)


class PredictionBody(BaseModel):
    order_id: int
    wait_minutes: int
    radius_m: int


class SimSpeedBody(BaseModel):
    speed: float = Field(gt=0, le=240)


class AdminLoginBody(BaseModel):
    username: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=1, max_length=256)


class CheckoutEstimateBody(BaseModel):
    cell: int = Field(default=DEFAULT_CHECKOUT_CELL, ge=0, le=99)
    value: int = Field(gt=0, le=100_000)
    n_items: int = Field(ge=1, le=100)


@router.post("/admin/login")
def admin_login(body: AdminLoginBody, response: Response):
    if not credentials_configured():
        raise HTTPException(
            503,
            "Admin sign-in is not configured. Set SHAREDCART_ADMIN_USERNAME, "
            "SHAREDCART_ADMIN_PASSWORD, and a SHAREDCART_ADMIN_SECRET of at least 32 characters.",
        )
    if not verify_credentials(body.username, body.password):
        raise HTTPException(401, "Invalid admin ID or password")
    response.set_cookie(
        ADMIN_COOKIE,
        create_admin_session(),
        max_age=ADMIN_SESSION_SECONDS,
        httponly=True,
        secure=os.getenv("SHAREDCART_COOKIE_SECURE", "").lower() == "true",
        samesite="strict",
        path="/",
    )
    return {"authenticated": True}


@router.get("/admin/session")
def admin_session(request: Request):
    return {"authenticated": valid_admin_session(request.cookies.get(ADMIN_COOKIE))}


@router.post("/admin/logout")
def admin_logout(response: Response):
    response.delete_cookie(ADMIN_COOKIE, path="/", httponly=True, samesite="strict")
    return {"authenticated": False}


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
def catalog(
    q: str | None = None,
    category: str | None = None,
    limit: int = Query(default=12, ge=1, le=100),
    page: int = Query(default=1, ge=1),
):
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
    count = int(len(df))
    start = (page - 1) * limit
    return {
        "disclaimer": "Sample grocery catalogue from the BlinkIT/BigMart item table used in the capstone simulation. These are not live restaurant menu items.",
        "categories": categories,
        "zones": zones,
        "count": count,
        "page": page,
        "page_size": limit,
        "items": df.iloc[start : start + limit].to_dict(orient="records"),
    }


@router.get("/simulation/status")
def sim_status(_: None = Depends(require_admin)):
    return get_runtime().status()


@router.post("/simulation/start")
def sim_start(_: None = Depends(require_admin)):
    return get_runtime().start()


@router.post("/simulation/pause")
def sim_pause(_: None = Depends(require_admin)):
    return get_runtime().pause()


@router.post("/simulation/resume")
def sim_resume(_: None = Depends(require_admin)):
    return get_runtime().resume()


@router.post("/simulation/reset")
def sim_reset(start_day: int = 7, _: None = Depends(require_admin)):
    return get_runtime().reset(persist_customers=True, start_day=start_day)


@router.post("/simulation/step")
def sim_step(n: int = Query(default=1, ge=1, le=500), _: None = Depends(require_admin)):
    return get_runtime().step(n)


@router.post("/simulation/speed")
def sim_speed(body: SimSpeedBody, _: None = Depends(require_admin)):
    return get_runtime().set_speed(body.speed)


@router.get("/orders")
def list_orders(
    source: str | None = None,
    status: str | None = None,
    q: str | None = None,
    _: None = Depends(require_admin),
):
    return {"orders": get_runtime().list_orders(source=source, q=q, status=status)}


@router.post("/orders")
def create_order(body: CheckoutBody):
    if not body.items:
        raise HTTPException(400, "Cart is empty")
    try:
        catalog = load_or_build_catalog().set_index("item_id")
    except FileNotFoundError as exc:
        raise HTTPException(503, str(exc))
    trusted_items = []
    for item in body.items:
        if item.item_id not in catalog.index:
            raise HTTPException(400, f"Unknown catalogue item: {item.item_id}")
        record = catalog.loc[item.item_id]
        price = int(record["item_price"])
        if item.unit_price != price:
            raise HTTPException(409, "Catalogue prices changed. Refresh the storefront and try again.")
        trusted_items.append(
            {
                "item_id": item.item_id,
                "item_type": str(record["item_type"]),
                "unit_price": price,
                "quantity": item.quantity,
            }
        )
    order = get_runtime().place_customer_order(
        trusted_items, body.cell, body.customer_name
    )
    access_key = order.pop("_access_key")
    return {
        "order": _customer_order(order),
        "access_key": access_key,
        "message": "Simulated checkout only — no payment was collected.",
    }


def _customer_order(order: dict[str, Any]) -> dict[str, Any]:
    public = _public_order(order)
    for private_key in ("user_id", "cell", "partner_order_id", "partner_order_ids"):
        public.pop(private_key, None)
    return public


@router.get("/orders/{order_id}")
def get_order(order_id: int, access_key: str | None = Header(default=None, alias="X-Order-Access-Key")):
    order = get_runtime().get_order(order_id)
    if not order or not valid_order_access_key(access_key, order.get("access_key_hash")):
        raise HTTPException(404, "Order not found")
    return {"order": _customer_order(order)}


@router.get("/orders/{order_id}/tracking")
def tracking(order_id: int, access_key: str | None = Header(default=None, alias="X-Order-Access-Key")):
    payload = get_runtime().tracking(order_id)
    if not payload or not valid_order_access_key(
        access_key, payload.get("order", {}).get("access_key_hash")
    ):
        raise HTTPException(404, "Order not found")
    payload["order"] = _customer_order(payload["order"])
    return payload


@router.post("/pooling/estimate")
def pooling_estimate(body: CheckoutEstimateBody):
    try:
        return get_runtime().estimate_checkout(body.value, body.n_items, body.cell)
    except ModelNotAvailable as exc:
        raise HTTPException(503, str(exc))


@router.post("/predictions")
def predictions(body: PredictionBody, _: None = Depends(require_admin)):
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
def dashboard(_: None = Depends(require_admin)):
    return get_runtime().dashboard()


@router.get("/models/metrics")
def model_metrics(_: None = Depends(require_admin)):
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
def impact(_: None = Depends(require_admin)):
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
def impact_recompute(body: ImpactBody, _: None = Depends(require_admin)):
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
def datasets_summary(_: None = Depends(require_admin)):
    return {"datasets": list_summaries()}


@router.get("/datasets/{name}")
def dataset_detail(name: str, _: None = Depends(require_admin)):
    try:
        return preview(name)
    except KeyError:
        raise HTTPException(404, "Unknown dataset")
    except FileNotFoundError:
        raise HTTPException(404, "Dataset file is not on disk. Run scripts/generate_artefacts.py")
